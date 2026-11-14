"""보험사 공시실 Ulixee Hero passive probe 실행기 (보험사 비종속 일반 래퍼).

목적
    insurer_disclosure_hero_probe.js(Node, Ulixee Hero)를 subprocess로 실행해
    공시실 페이지 구조(목록·상세·다운로드 방식)를 읽기 전용으로 판별한다.
    보험사 이름은 소스에 넣지 않고 --insurer 인자(영문 소문자 슬러그)로만 받는다.

입력
    --insurer <slug>   예: heungkuklife  (영문 소문자/숫자/_ 1~64자, 결과 폴더 이름)
    --url <URL>        공시실 URL. 여러 번 줄 수 있다.
    --dry-run          (기본) 실행 계획만 출력하고 브라우저를 띄우지 않는다.
    --execute          실제 probe 실행(읽기 전용: 이동·HTML 읽기·스크린샷).

저장 위치
    config.OUTPUT_PATH/insurance_docs/<insurer>/hero_probe/<KST 타임스탬프>/
    DB는 사용하지 않는다(common.database 미사용: 이 단계는 구조 판별만 함).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# 프로젝트 루트(/data/vm_project)를 import 경로에 넣어 루트 config.py·common 모듈을 쓴다(사용자 지침 4).
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402 - 공통 설정(OUTPUT_PATH)
from common.common_function import now_kst_iso, write_json_atomic  # noqa: E402 - 공통 기능

# Hero node_modules 위치와 JS 스크립트 위치(같은 폴더). 사이트 정보는 없다.
HERO_DIR = ROOT / "haness" / "apps" / "ulixee_hero_mcp"
JS_PATH = Path(__file__).with_suffix(".js")
SLUG_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
NODE_TIMEOUT_SECONDS = 110  # MCP 실행 도구 상한(120초) 안에서 끝내기 위한 값


def parse_args(argv: list[str]) -> argparse.Namespace:
    """인자 검증. 잘못된 입력은 SystemExit(2)로 끝난다(테스트 대상)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--insurer", required=True)
    parser.add_argument("--url", action="append", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not SLUG_PATTERN.match(args.insurer):
        parser.error("--insurer 는 영문 소문자/숫자/_ 1~64자여야 합니다")
    for url in args.url:
        if not re.match(r"^https?://", url):
            parser.error(f"http/https URL만 허용합니다: {url}")
    return args


def build_command(args: argparse.Namespace, out_dir: Path) -> list[str]:
    """node 실행 명령을 만든다(셸 문자열이 아닌 리스트: 인자 주입 방지)."""
    command = ["node", str(JS_PATH), "--hero-dir", str(HERO_DIR), "--out-dir", str(out_dir)]
    for url in args.url:
        command += ["--url", url]
    return command


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    stamp = now_kst_iso().replace(":", "").replace("-", "")[:15]  # 예: 20261102T013000
    out_dir = Path(config.OUTPUT_PATH) / "insurance_docs" / args.insurer / "hero_probe" / stamp
    command = build_command(args, out_dir)
    plan = {
        "mode": "execute" if args.execute else "dry-run",
        "insurer": args.insurer,
        "urls": args.url,
        "out_dir": str(out_dir),
        "command": command,
        # 실행 전 점검: node·Hero 설치 여부(없으면 실행하지 않음)
        "node_path": shutil.which("node"),
        "hero_installed": (HERO_DIR / "node_modules" / "@ulixee" / "hero").is_dir(),
        "js_exists": JS_PATH.is_file(),
        "checked_at": now_kst_iso(),
    }
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if (plan["node_path"] and plan["hero_installed"] and plan["js_exists"]) else 1

    if not (plan["node_path"] and plan["hero_installed"] and plan["js_exists"]):
        print(json.dumps({**plan, "ok": False, "error": "node 또는 Hero 미설치"}, ensure_ascii=False))
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=NODE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        result = {**plan, "ok": False, "error": f"node {NODE_TIMEOUT_SECONDS}초 초과"}
        write_json_atomic(out_dir / "run_summary.json", result)
        print(json.dumps(result, ensure_ascii=False))
        return 1
    # JS는 stdout 마지막 줄에 JSON을 쓴다. 파싱 실패 시 원문 일부를 남긴다.
    last_line = (completed.stdout.strip().splitlines() or [""])[-1]
    try:
        probe = json.loads(last_line)
    except json.JSONDecodeError:
        probe = {"ok": False, "raw_stdout_tail": completed.stdout[-2000:]}
    result = {**plan, "returncode": completed.returncode, "stderr_tail": completed.stderr[-2000:], "probe": probe}
    write_json_atomic(out_dir / "run_summary.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if completed.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
