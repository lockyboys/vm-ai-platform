"""harness/scripts/fix_provider_fatal_stop_20261114.py 실행 감싸기 (실행 도구가 FastAPI/LangGraph 소스만 허용).

APPLY_FLAG 파일(같은 폴더의 run_fix_provider_fatal_stop_20261114.apply)이 있으면 --apply, 없으면 dry-run.
도구 argv가 SSH 인자로 쓰여 인자를 직접 넘길 수 없어서 플래그 파일로 구분한다.
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
target = ROOT / "harness/scripts/fix_provider_fatal_stop_20261114.py"
# 2026-11-14 반영 완료: 두 번 반영되지 않도록 플래그 파일을 더 이상 보지 않고 항상 dry-run으로 실행한다.
apply_flag = Path(__file__).with_suffix(".apply_done_never_match")
sys.argv = [str(target)] + (["--apply"] if apply_flag.exists() else [])
runpy.run_path(str(target), run_name="__main__")
