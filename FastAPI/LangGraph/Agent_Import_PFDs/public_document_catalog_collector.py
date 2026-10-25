"""공개 문서 카탈로그 수집기 (사이트 비종속 일반 엔진).

목적
    기관 공시실처럼 "목록 API를 여러 단계로 내려가 파일명을 얻고, 다운로드 URL로
    PDF를 받는" 구조의 사이트를 프로파일(JSON 데이터)만으로 수집한다.
    사이트별 URL·요청 본문·응답 필드명은 profiles/<name>.json에만 두고, 이 엔진은
    특정 사이트 이름이나 필드명을 알지 못한다(사용자 지시: 특정 사이트 커스터마이징 금지).

실행 방식 (MCP 120초 상한 대응)
    MCP 실행 도구(mcp_codex_apps_run_python_source)는 120초 상한이 MCP 서버 프로세스에
    고정되어 있다. 그래서 AIA 수집기와 같은 방식으로 start 모드가 start_new_session=True
    분리 워커를 띄우고 즉시 반환한다. 워커 내부에서 사용자 승인 시간(최대 30,000초)을
    마감시각으로 관리하고, 마감 시 상태를 TIME_LIMIT로 남긴 뒤 종료한다(다음 start에서 이어받기).

입력 (stdin JSON)
    {"mode": "probe"|"start"|"status", "profile": "<이름>", "time_limit_seconds": <1~30000, 선택>}
    - probe : dry-run. 시드 페이지와 첫 시드의 1단계만 조회. 파일 저장/다운로드 없음.
    - start : 분리 워커 기동(카탈로그 수집 -> PDF 다운로드).
    - status: status.json과 산출물 위치 반환.

저장 위치
    config.OUTPUT_PATH/insurance_docs/<profile name>/ (루트 config.py 공통 설정 사용)
    DB 저장 요청은 없으므로 DB 연결/변경은 하지 않는다(common.database 미사용).
"""
from __future__ import annotations

import codecs
import concurrent.futures
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterator

# 프로젝트 루트(/data/vm_project)를 import 경로에 넣어 루트 config.py와 common 모듈을 사용한다.
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402 - 루트 경로를 sys.path에 넣은 뒤 가져와야 한다(사용자 지침 4: 공통 설정)
# 공통 기능은 common/common_function.py에서 가져온다(사용자 지침 4). 기존 함수 이름은 별칭으로 유지해
# 엔진 내부 호출과 기존 테스트가 그대로 동작하게 한다.
from common.common_function import (  # noqa: E402
    inspect_pdf_file as inspect_pdf,
    now_kst_iso as now,
    validate_safe_pdf_filename as safe_pdf_name,
    write_json_atomic as atomic_json,
)

# 상한·기준값은 루트 config.PUBLIC_DOCUMENT_COLLECTOR에서 읽는다(소스에 박지 않음).
_SETTINGS = config.PUBLIC_DOCUMENT_COLLECTOR
PROFILE_DIR = Path(_SETTINGS["profile_dir"])
MAX_TIME_LIMIT_SECONDS = int(_SETTINGS["max_time_limit_seconds"])  # LuckyBoys 승인 30,000초
MAX_PDF_BYTES = int(_SETTINGS["max_pdf_bytes"])                    # 비정상 대용량 응답 차단
MIN_FREE_DISK_BYTES = int(_SETTINGS["min_free_disk_bytes"])        # 서버 디스크 고갈 방지
NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
VAR_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(\|q)?\}")


class TimeLimitReached(Exception):
    """워커 마감시각 도달. 진행 결과는 보존되고 다음 start에서 이어받는다."""


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------
def validate_time_limit(value: Any) -> int:
    """시간 제한은 1~30000초 정수만 허용한다(bool/문자/None 거부)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("time_limit_seconds must be an integer")
    if not 1 <= value <= MAX_TIME_LIMIT_SECONDS:
        raise ValueError(f"time_limit_seconds must be 1..{MAX_TIME_LIMIT_SECONDS}")
    return value


def check_deadline(deadline: float) -> None:
    """요청 사이마다 호출해 마감시각을 넘기면 즉시 중단한다."""
    if time.monotonic() >= deadline:
        raise TimeLimitReached("time limit reached")


# ---------------------------------------------------------------------------
# 프로파일 검증 (사이트 정보는 데이터로만 받는다)
# ---------------------------------------------------------------------------
def validate_profile(profile: Any) -> dict:
    """프로파일 스키마를 검증한다. 잘못된 프로파일로 임의 호스트/경로에 접근하지 않게 막는다."""
    if not isinstance(profile, dict):
        raise ValueError("profile must be an object")
    name = profile.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ValueError("profile name must match [a-z0-9_]{1,64}")
    base = urllib.parse.urlsplit(str(profile.get("base_url", "")))
    hosts = profile.get("allowed_hosts")
    if base.scheme not in {"http", "https"} or not base.hostname:
        raise ValueError("base_url must be HTTP(S)")
    if not isinstance(hosts, list) or base.hostname not in hosts:
        raise ValueError("base_url host must be listed in allowed_hosts")
    seeds = profile.get("seeds")
    if not isinstance(seeds, dict) or not isinstance(seeds.get("pages"), list) or not seeds["pages"]:
        raise ValueError("seeds.pages must be a non-empty list")
    # 2026-10-25: pattern이 없으면 "패턴 없는 시드"(페이지 vars만 시드로 사용, 페이지 미조회).
    # 자동 탐색기가 만든 프로파일은 첫 단계 API가 최상위 분류를 돌려주므로 HTML 정규식이 필요 없다.
    if "pattern" in seeds or "groups" in seeds:
        pattern = re.compile(str(seeds.get("pattern", "")))
        groups = seeds.get("groups")
        if not isinstance(groups, list) or pattern.groups != len(groups) or not groups:
            raise ValueError("seeds.groups count must match pattern groups")
    for page in seeds["pages"]:
        if not isinstance(page, dict) or not str(page.get("url", "")).startswith("/"):
            raise ValueError("seed page url must be a site-relative path")
        if not isinstance(page.get("vars", {}), dict):
            raise ValueError("seed page vars must be an object")
    steps = profile.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps must be a non-empty list")
    for step in steps:
        if not isinstance(step, dict) or not str(step.get("url", "")).startswith("/"):
            raise ValueError("step url must be a site-relative path")
        if not isinstance(step.get("body"), dict) or not isinstance(step.get("export"), dict):
            raise ValueError("step body/export must be objects")
        if not isinstance(step.get("list_path"), str):
            raise ValueError("step list_path must be text")
    document = profile.get("document")
    if not isinstance(document, dict) or not document.get("file_var") or not document.get("url_template"):
        raise ValueError("document.file_var and document.url_template are required")
    # 문서 주소: 사이트 상대경로, 또는 allowed_hosts에 있는 별도 문서 서버의 절대 URL(2026-10-25)
    template = str(document["url_template"])
    if not template.startswith("/"):
        absolute = urllib.parse.urlsplit(template)
        if absolute.scheme not in {"http", "https"} or absolute.hostname not in hosts:
            raise ValueError("document url_template must be site-relative or on an allowed host")
    # 폼 본문 문자셋(예: 국내 ASP 사이트 cp949). 알 수 없는 문자셋은 거부한다.
    try:
        codecs.lookup(str(document.get("body_charset", "utf-8")))
    except LookupError:
        raise ValueError("document.body_charset is not a known encoding") from None
    # 2026-10-25: 다운로드가 폼 POST인 사이트 지원(method=POST + body 템플릿). 기본은 GET.
    if str(document.get("method", "GET")).upper() not in {"GET", "POST"}:
        raise ValueError("document.method must be GET or POST")
    if "body" in document and not isinstance(document["body"], dict):
        raise ValueError("document.body must be an object")
    validate_time_limit(profile.get("time_limit_seconds", MAX_TIME_LIMIT_SECONDS))
    return profile


def load_profile(name: str) -> dict:
    """profiles/<name>.json만 읽는다(이름 검증으로 경로 이탈 차단)."""
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ValueError("invalid profile name")
    return validate_profile(json.loads((PROFILE_DIR / f"{name}.json").read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# 템플릿/탐색 (사이트 비종속)
# ---------------------------------------------------------------------------
def render(template: Any, ctx: dict) -> Any:
    """{var}는 컨텍스트 값으로, {var|q}는 URL 인코딩 값으로 치환한다.

    문자열 전체가 "{var}" 하나면 원래 타입(숫자 등)을 유지한다(API가 숫자를 기대할 수 있음).
    정의되지 않은 변수는 빈 값으로 넘기지 않고 오류로 처리한다(잘못된 요청 방지).
    """
    if isinstance(template, dict):
        return {key: render(value, ctx) for key, value in template.items()}
    if isinstance(template, list):
        return [render(value, ctx) for value in template]
    if not isinstance(template, str):
        return template
    whole = VAR_PATTERN.fullmatch(template)
    if whole and not whole.group(2):
        if whole.group(1) not in ctx:
            raise ValueError(f"undefined template variable: {whole.group(1)}")
        return ctx[whole.group(1)]

    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in ctx:
            raise ValueError(f"undefined template variable: {key}")
        text = "" if ctx[key] is None else str(ctx[key])
        return urllib.parse.quote(text, safe="") if match.group(2) else text

    return VAR_PATTERN.sub(replace, template)


def extract_seeds(html: str, pattern: str, groups: list[str], base_vars: dict) -> list[dict]:
    """목록 화면 HTML에서 시드(최상위 분류) 값을 정규식으로 추출한다. 0건은 오류."""
    seeds, seen = [], set()
    for match in re.finditer(pattern, html):
        seed = {**base_vars, **dict(zip(groups, match.groups()))}
        key = json.dumps(seed, ensure_ascii=False, sort_keys=True)
        if key not in seen:        # 같은 화면에 메뉴가 중복 출력돼도 한 번만 탐색
            seen.add(key)
            seeds.append(seed)
    if not seeds:
        raise ValueError("no seeds found; page may be blocked or changed")
    return seeds


def list_at(data: Any, path: str) -> list:
    """응답 JSON에서 목록을 꺼낸다. 오류 응답이나 목록이 아닌 값은 성공으로 세지 않는다."""
    if not isinstance(data, dict) or "errMsg" in data:
        raise ValueError("API returned an error or non-object response")
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"list path not found: {path}")
        value = value[part]
    if not isinstance(value, list):
        raise ValueError(f"value at {path} is not a list")
    return value


def walk_steps(steps: list[dict], ctx: dict, fetch: Callable[[str, Any], Any],
               deadline: float) -> Iterator[dict]:
    """단계를 깊이 우선으로 내려가며 마지막 단계 결과를 행(컨텍스트)으로 내보낸다.

    상위 단계 변수는 하위 행에 그대로 전달되어 출처 추적(상품군·판매상태 등)에 쓰인다.
    """
    if not steps:
        yield ctx
        return
    check_deadline(deadline)
    step = steps[0]
    data = fetch(render(step["url"], ctx), render(step["body"], ctx))
    for item in list_at(data, step["list_path"]):
        if not isinstance(item, dict):
            raise ValueError("list item must be an object")
        child = {**ctx, **{var: item.get(field) for var, field in step["export"].items()}}
        yield from walk_steps(steps[1:], child, fetch, deadline)


def build_targets(rows: list[dict], file_var: str, subdir_var: str | None) -> tuple[list[dict], int]:
    """파일명 기준으로 중복을 제거하고 모든 출처 참조를 보존한다. 파일 없음/불안전 이름은 missing."""
    targets: dict[str, dict] = {}
    missing = 0
    for row in rows:
        try:
            name = safe_pdf_name(row.get(file_var))
        except ValueError:
            missing += 1
            continue
        subdir = str(row.get(subdir_var) or "") if subdir_var else ""
        target = targets.setdefault(name, {"file": name, "subdir": subdir, "references": []})
        target["references"].append(row)
    return list(targets.values()), missing


def encode_form(form: dict, charset: str = "utf-8") -> bytes:
    """폼 본문을 지정 문자셋으로 URL 인코딩한다(cp949 사이트 지원)."""
    return urllib.parse.urlencode(form, encoding=charset).encode("ascii")


def document_request(document: dict, file_name: str) -> tuple[str, dict | None]:
    """다운로드 요청(경로, 폼 본문)을 만든다. GET이면 본문은 None.

    url_template과 body 모두 {file_var}/{file_var|q} 치환을 쓴다(사이트 정보는 프로파일 데이터).
    """
    ctx = {document["file_var"]: file_name}
    url = render(document["url_template"], ctx)
    if str(document.get("method", "GET")).upper() == "POST":
        return url, render(document.get("body", {}), ctx)
    return url, None


def parse_options(options: Any) -> dict:
    """stdin 제어값 검증. 정해진 모드·프로파일 이름·시간 제한 외 입력은 거부한다."""
    if not isinstance(options, dict):
        raise ValueError("options must be an object")
    mode = options.get("mode")
    if mode not in {"probe", "start", "status"}:
        raise ValueError("mode must be probe|start|status")
    profile = options.get("profile")
    if not isinstance(profile, str) or not NAME_PATTERN.fullmatch(profile):
        raise ValueError("profile name required ([a-z0-9_])")
    result = {"mode": mode, "profile": profile}
    # self_heal: probe 실패 시 profile_autodiscover로 재탐색·실검증·저장 후 재probe(2026-10-25)
    if "self_heal" in options:
        if not isinstance(options["self_heal"], bool):
            raise ValueError("self_heal must be true or false")
        result["self_heal"] = options["self_heal"]
    if "time_limit_seconds" in options:
        result["time_limit_seconds"] = validate_time_limit(options["time_limit_seconds"])
    return result


# ---------------------------------------------------------------------------
# HTTP (허용 호스트만, 일시 오류만 재시도)
# ---------------------------------------------------------------------------
class SiteClient:
    """프로파일의 base_url/헤더/본문 형식으로 요청한다. 리다이렉트 호스트도 허용 목록으로 검사."""

    def __init__(self, profile: dict):
        self.profile = profile
        self.base = profile["base_url"].rstrip("/")
        self.hosts = set(profile["allowed_hosts"])
        req = profile.get("request", {})
        self.headers = dict(req.get("headers", {}))
        self.method = req.get("method", "POST")
        self.body_format = req.get("body_format", "json")
        self.delay = float(req.get("delay_seconds", 0.3))
        self.timeout = float(req.get("timeout_seconds", 45))

    def _open(self, url: str, data: bytes | None, headers: dict):
        """재시도 3회(429/5xx/네트워크 오류만). 인증/차단 응답은 재시도하지 않는다."""
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, data=data, headers=headers,
                                                 method="POST" if data is not None else "GET")
                response = urllib.request.urlopen(request, timeout=self.timeout)
                if urllib.parse.urlsplit(response.url).hostname not in self.hosts:
                    response.close()
                    raise ValueError("redirected to a host outside allowed_hosts")
                return response
            except urllib.error.HTTPError as error:
                error.close()
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
            time.sleep(2 ** attempt)
        raise RuntimeError("unexpected retry exhaustion")

    def get_text(self, path: str) -> str:
        with self._open(self.base + path, None, self.headers) as response:
            raw = response.read()
        time.sleep(self.delay)
        return raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")

    def fetch_json(self, path: str, body: Any) -> Any:
        """목록 API 호출. JSON 또는 폼 본문을 프로파일 설정대로 보낸다."""
        headers = dict(self.headers)
        if self.body_format == "json":
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        else:
            data = urllib.parse.urlencode(body).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        with self._open(self.base + path, data, headers) as response:
            raw = response.read()
        time.sleep(self.delay)
        try:
            return json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError:
            return json.loads(raw.decode("cp949"))

    def download(self, path: str, dest: Path, form: dict | None = None, charset: str = "utf-8") -> dict:
        """.part에 받아 PDF 검증 후 원자적으로 설치한다. 실패 시 부분 파일 삭제.

        form이 있으면 폼 POST로 요청한다(2026-10-25, POST 다운로드 사이트 지원)."""
        if shutil.disk_usage(dest.parent).free < MIN_FREE_DISK_BYTES:
            raise OSError("less than 1 GiB free disk space")
        part = dest.with_name(dest.name + ".part")
        headers = dict(self.headers)
        data = None
        if form is not None:
            data = encode_form(form, charset)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        # 별도 문서 서버의 절대 URL이면 그대로 쓴다(호스트는 _open에서 allowed_hosts로 재검사).
        url = path if path.startswith(("http://", "https://")) else self.base + path
        if urllib.parse.urlsplit(url).hostname not in self.hosts:
            raise ValueError("document host is not in allowed_hosts")
        try:
            with self._open(url, data, headers) as response, part.open("wb") as out:
                total = 0
                for chunk in iter(lambda: response.read(128 * 1024), b""):
                    total += len(chunk)
                    if total > MAX_PDF_BYTES:
                        raise ValueError("PDF exceeds 512 MiB limit")
                    out.write(chunk)
            info = inspect_pdf(part)
            os.replace(part, dest)
            time.sleep(self.delay)
            return info
        finally:
            part.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 실행 모드
# ---------------------------------------------------------------------------
def output_dir(profile: dict) -> Path:
    """루트 config.OUTPUT_PATH 아래 프로파일별 폴더(공통 설정 지침 4번)."""
    from common.common_function import normalize_required_text
    base = Path(normalize_required_text(str(config.OUTPUT_PATH), "OUTPUT_PATH")).resolve()
    out = base / str(_SETTINGS["output_subdir"]) / profile["name"]
    out.mkdir(parents=True, exist_ok=True)
    return out


def collect_seeds(client: SiteClient, profile: dict) -> list[dict]:
    seeds_cfg = profile["seeds"]
    seeds: list[dict] = []
    for page in seeds_cfg["pages"]:
        if "pattern" not in seeds_cfg:
            # 패턴 없는 시드: 페이지를 읽지 않고 vars를 그대로 시드로 쓴다.
            seeds.append(dict(page.get("vars", {})))
            continue
        html = client.get_text(page["url"])
        seeds += extract_seeds(html, seeds_cfg["pattern"], seeds_cfg["groups"], dict(page.get("vars", {})))
    return seeds


def probe(profile: dict) -> dict:
    """dry-run: 시드 수와 첫 시드 1단계 결과 건수만 확인. 파일 저장·다운로드 없음."""
    client = SiteClient(profile)
    seeds = collect_seeds(client, profile)
    step = profile["steps"][0]
    first = list_at(client.fetch_json(render(step["url"], seeds[0]), render(step["body"], seeds[0])),
                    step["list_path"])
    per_page = {}
    for seed in seeds:
        label = json.dumps({k: seed.get(k) for k in profile["seeds"]["pages"][0].get("vars", {})},
                           ensure_ascii=False)
        per_page[label] = per_page.get(label, 0) + 1
    return {"mode": "probe", "profile": profile["name"], "seed_count": len(seeds),
            "seeds_per_page": per_page, "first_seed": seeds[0],
            "first_step_items": len(first), "first_step_sample": first[:3],
            "files_written": 0, "checked_kst": now()}


AUTODISCOVER_PATH = Path(__file__).resolve().with_name("profile_autodiscover.py")


def self_heal_profile(name: str) -> dict:
    """profile_autodiscover.auto(apply=True)를 호출해 프로파일을 재탐색·실검증·저장한다.

    시작 URL·문서 키워드는 저장된 프로파일의 autodiscover 블록에서 읽으므로 사람 입력이 필요 없다.
    엔진과 탐색기를 같은 사이트 비종속 원칙으로 분리하려고 경로로 직접 로드한다(순환 import 방지).
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("profile_autodiscover_heal", AUTODISCOVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.auto({"mode": "auto", "name": name, "apply": True})


def run_probe(name: str, heal: bool, load: Callable[[str], dict] = None,
              probe_fn: Callable[[dict], dict] = None, heal_fn: Callable[[str], dict] = None) -> dict:
    """probe를 실행하고, 실패하면(heal=True일 때) 스스로 재탐색한 뒤 새 프로파일로 다시 probe한다.

    - 성공: probe 결과 그대로 반환(재탐색 없음).
    - 실패 + heal=False: 원래 예외를 그대로 올린다.
    - 실패 + heal=True: 재탐색 결과가 FAILED면 RuntimeError(실패를 성공처럼 숨기지 않음),
      성공이면 {"first_error", "self_heal", "probe"}를 반환한다.
    """
    load = load or load_profile
    probe_fn = probe_fn or probe
    heal_fn = heal_fn or self_heal_profile
    try:
        return probe_fn(load(name))
    except Exception as error:  # noqa: BLE001 - 어떤 실패든 재탐색 대상
        if not heal:
            raise
        first_error = f"{type(error).__name__}: {str(error)[:300]}"
    report = heal_fn(name) or {}
    if str(report.get("result", "FAILED")).startswith("FAILED"):
        raise RuntimeError(f"self_heal failed after probe error ({first_error}): "
                           f"{json.dumps(report, ensure_ascii=False, default=str)[:800]}")
    return {"first_error": first_error, "self_heal": {k: v for k, v in report.items() if k != "attempts"},
            "probe": probe_fn(load(name))}


def ensure_healthy(profile: dict, probe_fn: Callable[[dict], dict] = None,
                   heal_fn: Callable[[str], dict] = None,
                   load: Callable[[str], dict] = None) -> tuple[dict, dict | None]:
    """워커 시작 전 점검(P0, 2026-10-25). 실패하면 워커 안에서 스스로 재탐색해 새 프로파일을 돌려준다.

    - 워커는 systemd 유닛에서 돌기 때문에 MCP 120초 제한 없이 브라우저 재탐색(약 100초)을 할 수 있다.
    - autodiscover 블록(시작 URL·키워드)이 없는 수동 프로파일은 추측하지 않고 원래 오류를 올린다.
    - 재탐색도 실패하면 RuntimeError로 워커를 FAILED 처리한다(실패를 성공처럼 남기지 않음).
    반환: (사용할 프로파일, 재탐색 보고 또는 None)
    """
    probe_fn = probe_fn or probe
    heal_fn = heal_fn or self_heal_profile
    load = load or load_profile
    try:
        probe_fn(profile)
        return profile, None
    except Exception as error:  # noqa: BLE001 - 어떤 점검 실패든 재탐색 대상
        if not profile.get("autodiscover"):
            raise
        first_error = f"{type(error).__name__}: {str(error)[:300]}"
    report = heal_fn(profile["name"]) or {}
    if str(report.get("result", "FAILED")).startswith("FAILED"):
        raise RuntimeError(f"self_heal failed after check error ({first_error}): "
                           f"{json.dumps(report, ensure_ascii=False, default=str)[:800]}")
    summary = {k: v for k, v in report.items() if k != "attempts"}
    summary["first_error"] = first_error
    summary["healed_kst"] = now()
    return load(profile["name"]), summary


def should_heal_after_catalog(state: dict, already_healed: bool) -> bool:
    """수집 중 모든 시드가 실패했으면 사이트 구조가 바뀐 것으로 보고 재탐색한다(한 워커에서 1회만).

    일부만 실패한 경우는 일시 오류로 보고 다음 실행의 이어받기에 맡긴다(불필요한 재탐색 방지).
    """
    total = int(state.get("seeds_total", 0))
    return not already_healed and total > 0 and int(state.get("seed_failures", 0)) >= total


def run_catalog_round(seeds: list[dict], profile: dict, client: SiteClient, out: Path, done: set,
                      done_path: Path, state: dict, seed_errors: list[dict], deadline: float) -> None:
    """시드 목록 1회분 카탈로그 수집(기존 워커 루프를 재탐색 후 재사용할 수 있게 분리, 동작 동일).

    끝까지 성공한 시드만 done에 넣고, 실패 시드는 state/seed_failures.json에 남겨 다음 실행에서 재시도한다.
    """
    with (out / "catalog_rows.jsonl").open("a", encoding="utf-8") as catalog:
        for seed in seeds:
            key = json.dumps(seed, ensure_ascii=False, sort_keys=True)
            if key in done:
                continue
            check_deadline(deadline)
            try:
                rows = list(walk_steps(profile["steps"], seed, client.fetch_json, deadline))
            except TimeLimitReached:
                raise
            except Exception as error:
                state["seed_failures"] += 1
                seed_errors.append({"seed": seed, "error_type": type(error).__name__,
                                    "error": str(error)[:300], "checked_kst": now()})
                atomic_json(out / "seed_failures.json", seed_errors)
                continue
            for row in rows:
                catalog.write(json.dumps(row, ensure_ascii=False) + "\n")
            catalog.flush()
            done.add(key)
            atomic_json(done_path, sorted(done))
            state["seeds_done"] = len(done)
            state["updated_kst"] = now()
            atomic_json(out / "status.json", state)


def worker(profile: dict, time_limit: int) -> None:
    """분리 워커: 카탈로그 수집(시드 단위 이어받기) -> PDF 다운로드(파일 단위 이어받기)."""
    out = output_dir(profile)
    deadline = time.monotonic() + time_limit
    with (out / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)   # 중복 워커 차단
        state = {"state": "RUNNING", "phase": "CATALOG", "profile": profile["name"],
                 "pid": os.getpid(), "started_kst": now(), "time_limit_seconds": time_limit,
                 "seeds_total": 0, "seeds_done": 0, "seed_failures": 0, "catalog_rows": 0,
                 "targets": 0, "missing_file_rows": 0, "finished": 0, "success": 0, "failed": 0}
        atomic_json(out / "status.json", state)
        healed = False
        try:
            # 0) 시작 전 점검 → 실패 시 워커 안에서 스스로 재탐색(P0 자가 복구)
            profile, heal_report = ensure_healthy(profile)
            if heal_report:
                healed = True
                state["self_heal"] = heal_report
                atomic_json(out / "status.json", state)
            client = SiteClient(profile)
            done_path = out / "seeds_done.json"
            done = set(json.loads(done_path.read_text(encoding="utf-8"))) if done_path.exists() else set()
            seed_errors: list[dict] = []
            # 1) 카탈로그: 시드별로 끝까지 탐색이 성공해야 done 처리(중간 실패 시드는 다음 실행에서 재시도)
            #    모든 시드가 실패하면 구조 변경으로 보고 1회 재탐색 후 새 프로파일로 다시 수집한다.
            for _round in range(2):
                seeds = collect_seeds(client, profile)
                atomic_json(out / "seeds.json", seeds)
                state["seeds_total"] = len(seeds)
                state["seed_failures"] = 0
                seed_errors.clear()
                run_catalog_round(seeds, profile, client, out, done, done_path, state, seed_errors, deadline)
                if not should_heal_after_catalog(state, healed):
                    break
                report = self_heal_profile(profile["name"]) or {}
                if str(report.get("result", "FAILED")).startswith("FAILED"):
                    state["self_heal"] = {"result": "FAILED", "checked_kst": now()}
                    break
                healed = True
                state["self_heal"] = {k: v for k, v in report.items() if k != "attempts"} | {"healed_kst": now()}
                profile = load_profile(profile["name"])
                client = SiteClient(profile)
            state["seeds_done"] = len(done)

            # 2) 다운로드: 저장된 카탈로그 전체 기준, 기존 검증 파일은 재사용
            state["phase"] = "DOWNLOAD"
            rows = [json.loads(line) for line in (out / "catalog_rows.jsonl").read_text(encoding="utf-8").splitlines() if line]
            document = profile["document"]
            targets, missing = build_targets(rows, document["file_var"], document.get("subdir_var"))
            state.update({"catalog_rows": len(rows), "targets": len(targets), "missing_file_rows": missing})
            atomic_json(out / "targets.json", [{k: v for k, v in t.items() if k != "references"} |
                                               {"reference_count": len(t["references"])} for t in targets])
            atomic_json(out / "status.json", state)
            results = []

            def one(target: dict) -> dict:
                check_deadline(deadline)
                folder = out / "pdf" / (target["subdir"] or "_")
                folder.mkdir(parents=True, exist_ok=True)
                dest = folder / target["file"]
                if dest.exists():
                    try:
                        return {"file": target["file"], "status": "existing_verified", **inspect_pdf(dest)}
                    except ValueError:
                        dest.unlink(missing_ok=True)   # 손상 잔존 파일은 다시 받는다
                url, form = document_request(document, target["file"])
                return {"file": target["file"], "status": "downloaded_verified",
                        **client.download(url, dest, form, document.get("body_charset", "utf-8"))}

            hit_limit = False
            with (out / "manifest.jsonl").open("a", encoding="utf-8") as manifest:
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
                futures = {pool.submit(one, t): t for t in targets}
                try:
                    for future in concurrent.futures.as_completed(futures):
                        target = futures[future]
                        try:
                            result = future.result()
                            state["success"] += 1
                        except TimeLimitReached:
                            hit_limit = True
                            continue
                        except Exception as error:
                            result = {"file": target["file"], "status": "failed",
                                      "error_type": type(error).__name__, "error": str(error)[:300]}
                            state["failed"] += 1
                        result["subdir"] = target["subdir"]
                        result["checked_kst"] = now()
                        manifest.write(json.dumps(result, ensure_ascii=False) + "\n")
                        manifest.flush()
                        results.append(result)
                        state["finished"] += 1
                        state["updated_kst"] = now()
                        atomic_json(out / "status.json", state)
                finally:
                    pool.shutdown(wait=True, cancel_futures=True)
            atomic_json(out / "failures.json", [r for r in results if r["status"] == "failed"])
            if hit_limit:
                raise TimeLimitReached("time limit reached during download")
            complete = (state["seed_failures"] == 0 and state["failed"] == 0
                        and state["success"] == len(targets))
            state["state"] = "COMPLETE" if complete else "PARTIAL"
        except TimeLimitReached:
            state["state"] = "TIME_LIMIT"          # 다음 start에서 이어받기
        state["ended_kst"] = now()
        state["scope"] = "Files found in the saved public catalog snapshot only"
        atomic_json(out / "status.json", state)


def start(profile: dict, time_limit: int) -> dict:
    """워커를 MCP 서비스와 분리된 systemd 유닛으로 띄우고 바로 반환한다(2026-10-25 변경).

    이유: 기존 start_new_session 자식 프로세스는 sps-harness.service cgroup에 남아,
          MCP를 재시작하면 같이 꺼졌다(1차 워커 17시간 방치). systemd-run 유닛은 MCP 재시작과
          무관하게 끝까지 실행되므로, 이후에는 status로 가끔 확인만 하면 된다.
    명령: config.PUBLIC_DOCUMENT_COLLECTOR의 systemd_run_command(sudo -n systemd-run --collect --quiet),
          유닛 이름 = unit_prefix + 프로파일 이름(_→-). 로그는 journalctl -u <유닛>.
    실패: systemd-run이 0이 아닌 코드로 끝나면 RuntimeError(기동 실패를 성공으로 보고하지 않음).
    """
    out = output_dir(profile)
    with (out / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("collector worker already running")
        fcntl.flock(lock, fcntl.LOCK_UN)
    unit = f"{_SETTINGS['unit_prefix']}{profile['name'].replace('_', '-')}"
    command = [
        *_SETTINGS["systemd_run_command"],
        f"--unit={unit}",
        "-p", f"User={_SETTINGS['service_user']}",
        "-p", f"WorkingDirectory={ROOT}",
        sys.executable, str(Path(__file__).resolve()),
        "--worker", profile["name"], str(time_limit),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"systemd-run failed: rc={completed.returncode} {completed.stderr.strip()[:300]}")
    return {"started": True, "unit": unit, "profile": profile["name"],
            "time_limit_seconds": time_limit, "output_dir": str(out), "started_kst": now(),
            "check": f"journalctl -u {unit}  /  mode=status"}


def status(profile: dict) -> dict:
    out = output_dir(profile)
    path = out / "status.json"
    return {"output_dir": str(out),
            "status": json.loads(path.read_text(encoding="utf-8")) if path.exists() else "NOT_STARTED"}


def main() -> None:
    """stdin JSON 제어만 받는다. 임의 URL/명령은 받지 않는다(사이트 정보는 프로파일 파일)."""
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        profile = load_profile(sys.argv[2])
        try:
            worker(profile, validate_time_limit(int(sys.argv[3])))
        except BlockingIOError:
            return   # 이미 실행 중인 워커 상태를 덮어쓰지 않는다
        except Exception as error:
            atomic_json(output_dir(profile) / "status.json",
                        {"state": "FAILED", "error_type": type(error).__name__,
                         "error": str(error)[:300], "ended_kst": now()})
            raise
        return
    options = parse_options(json.loads(sys.stdin.read() or "{}"))
    profile = load_profile(options["profile"])
    limit = options.get("time_limit_seconds", profile.get("time_limit_seconds", MAX_TIME_LIMIT_SECONDS))
    if options["mode"] == "probe":
        result = run_probe(options["profile"], options.get("self_heal", False))
    elif options["mode"] == "start":
        result = start(profile, validate_time_limit(limit))
    else:
        result = status(profile)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
