"""일반화된 공개 문서 카탈로그 수집기 회귀 테스트.

목적: 사이트 정보는 프로파일(JSON 데이터)로만 주고, 엔진이 어떤 사이트에도
      같은 규칙(입력 검증·다단계 탐색·중복 제거·PDF 검증·시간 제한)을 지키는지 확인한다.
주의: 실제 네트워크 호출, PDF 다운로드, DB 연결은 하지 않는다(가짜 fetch 사용).
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "FastAPI/LangGraph/Agent_Import_PFDs"
MODULE_PATH = PKG / "public_document_catalog_collector.py"
PROFILE_PATH = PKG / "profiles/db_insurance_terms.json"


def load_module():
    """경로로 직접 로드한다. 파일이 없으면 구현 전 실패를 재현한다."""
    spec = importlib.util.spec_from_file_location("catalog_collector", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return load_module()


# 사이트와 무관한 가짜 프로파일: 엔진이 특정 사이트 이름/필드에 의존하지 않는지 확인용
FAKE_PROFILE = {
    "name": "fake_site",
    "base_url": "https://docs.example.org",
    "allowed_hosts": ["docs.example.org"],
    "request": {"method": "POST", "body_format": "json", "headers": {}},
    "seeds": {
        "pages": [{"url": "/list.do", "vars": {"status": "on"}}],
        "pattern": r"pick\('([^']*)','([^']*)'\)",
        "groups": ["group", "kind"],
    },
    "steps": [
        {"url": "/a.json", "body": {"g": "{group}", "k": "{kind}", "s": "{status}"},
         "list_path": "items", "export": {"name": "NAME"}},
        {"url": "/b.json", "body": {"n": "{name}"}, "list_path": "items",
         "export": {"file": "FILE", "start": "FROM"}},
    ],
    "document": {"file_var": "file", "url_template": "/down?f={file|q}", "subdir_var": "status"},
    "time_limit_seconds": 30000,
}


def test_profile_file_is_valid(mod):
    # 실제 사용할 DB손보 프로파일도 같은 스키마 검증을 통과해야 한다.
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    assert mod.validate_profile(profile)["name"] == "db_insurance_terms"


@pytest.mark.parametrize("broken", [
    {"steps": []},                                   # 단계 없음
    {"base_url": "ftp://x.org"},                     # 비 HTTP(S)
    {"base_url": "https://evil.org"},                # 허용 호스트 불일치
    {"name": "../x"},                                # 경로 이탈 이름
    {"document": {"url_template": "/d"}},            # file_var 누락
])
def test_invalid_profile_rejected(mod, broken):
    profile = copy.deepcopy(FAKE_PROFILE)
    profile.update(broken)
    with pytest.raises(ValueError):
        mod.validate_profile(profile)


def test_extract_seeds_generic(mod):
    html = "pick('A','1'); pick('B','2'); function pick(a, b) {"
    seeds = mod.extract_seeds(html, FAKE_PROFILE["seeds"]["pattern"], ["group", "kind"], {"status": "on"})
    assert seeds == [{"status": "on", "group": "A", "kind": "1"}, {"status": "on", "group": "B", "kind": "2"}]


def test_extract_seeds_empty_is_error(mod):
    # 0건은 차단 페이지일 수 있어 수집 완전성을 증명하지 못하므로 오류로 처리한다.
    with pytest.raises(ValueError):
        mod.extract_seeds("<html>blocked</html>", r"pick\('([^']*)'\)", ["g"], {})


def test_render_template(mod):
    ctx = {"a": "건강", "n": 10, "f": "약관_1(04).pdf"}
    assert mod.render({"x": "{a}", "y": "{n}", "z": "고정"}, ctx) == {"x": "건강", "y": 10, "z": "고정"}
    assert mod.render("/d?f={f|q}", ctx) == "/d?f=%EC%95%BD%EA%B4%80_1%2804%29.pdf"
    with pytest.raises(ValueError):
        mod.render("{missing}", ctx)  # 정의되지 않은 변수는 조용히 빈 값으로 두지 않는다


def test_walk_steps_with_fake_fetch(mod):
    # 2단계 탐색 결과가 리프 행으로 펼쳐지고, 상위 변수가 하위 행에 전달되어야 한다.
    responses = {
        "/a.json": {"items": [{"NAME": "P1"}, {"NAME": "P2"}]},
        "/b.json": {"items": [{"FILE": "t.pdf", "FROM": "20260101"}]},
    }
    calls = []

    def fake_fetch(url, body):
        calls.append((url, body))
        return responses[url]

    rows = list(mod.walk_steps(FAKE_PROFILE["steps"], {"group": "A", "kind": "1", "status": "on"}, fake_fetch,
                               deadline=time.monotonic() + 60))
    assert len(rows) == 2 and rows[0]["file"] == "t.pdf" and rows[1]["name"] == "P2"
    assert calls[0] == ("/a.json", {"g": "A", "k": "1", "s": "on"})


def test_api_list_rejects_error_response(mod):
    with pytest.raises(ValueError):
        mod.list_at({"errMsg": {"rspnCd": "-1000"}}, "result")
    with pytest.raises(ValueError):
        mod.list_at({"result": "x"}, "result")
    assert mod.list_at({"result": []}, "result") == []


@pytest.mark.parametrize("name", ["../약관.pdf", "a/b.pdf", "약관.exe", "", None, ".약관.pdf", "a\\b.pdf"])
def test_unsafe_filename_rejected(mod, name):
    with pytest.raises(ValueError):
        mod.safe_pdf_name(name)


def test_safe_filename_allowed(mod):
    assert mod.safe_pdf_name("약관_31085(04)_20260701.pdf") == "약관_31085(04)_20260701.pdf"


def test_targets_dedup_and_missing(mod):
    rows = [
        {"status": "on", "name": "A", "file": "t1.pdf"},
        {"status": "on", "name": "B", "file": "t1.pdf"},
        {"status": "off", "name": "C", "file": ""},
    ]
    targets, missing = mod.build_targets(rows, file_var="file", subdir_var="status")
    assert len(targets) == 1 and len(targets[0]["references"]) == 2 and missing == 1


def test_html_or_truncated_pdf_rejected(mod, tmp_path):
    path = tmp_path / "bad.pdf"
    for content in (b"<html>blocked</html>", b"%PDF-1.4 truncated", b""):
        path.write_bytes(content)
        with pytest.raises(ValueError):
            mod.inspect_pdf(path)


def test_valid_pdf_hash(mod, tmp_path):
    data = b"%PDF-1.4\nfixture\n%%EOF\n"
    path = tmp_path / "ok.pdf"
    path.write_bytes(data)
    assert mod.inspect_pdf(path) == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


@pytest.mark.parametrize("value", [0, -1, 30001, "abc", None])
def test_time_limit_out_of_range(mod, value):
    with pytest.raises(ValueError):
        mod.validate_time_limit(value)


def test_time_limit_max_allowed(mod):
    assert mod.validate_time_limit(30000) == 30000


def test_deadline_stops_loop(mod):
    with pytest.raises(mod.TimeLimitReached):
        mod.check_deadline(time.monotonic() - 1)


@pytest.mark.parametrize("options", [{"mode": "delete_all"}, {"mode": "start", "profile": "../etc"}, {"mode": "start"}])
def test_bad_options_rejected(mod, options):
    with pytest.raises(ValueError):
        mod.parse_options(options)
