"""메리츠화재 상품공시 페이지 passive probe 실행 감싸기 (2026-11-15, LuckyBoys 요청).

실행 도구가 FastAPI/LangGraph 소스만 실행하고 argv를 직접 넘길 수 없어서,
harness/scripts/insurer_disclosure_hero_probe.py 에 인자를 넣어 runpy로 실행한다.
- 읽기 전용(페이지 이동·HTML 읽기·스크린샷만). 로그인·CAPTCHA·접근통제 우회 없음.
- 대상: 메리츠화재 상품공시(note.do), 메인(main.do)
- 결과: config.OUTPUT_PATH/insurance_docs/meritzfire/hero_probe/<KST 시각>/
- 2026-11-15: Hero가 옛 경로(haness/apps/ulixee_hero_mcp)에만 설치되어 있어 원본 스크립트가
  "Hero 미설치"로 멈췄다. 원본은 건드리지 않고 이 감싸기에서 HERO_DIR만 실제 설치 경로로 바꿔 부른다.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "harness/scripts/insurer_disclosure_hero_probe.py"
INSTALLED_HERO_DIR = ROOT / "haness/apps/ulixee_hero_mcp"  # 실제 node_modules/@ulixee/hero 가 있는 곳
URLS = [
    "https://www.meritzfire.com/disclosure/product-announcement/note.do#!/",
    "https://www.meritzfire.com/main.do#!/",
]
argv = ["--insurer", "meritzfire", "--execute"]
for url in URLS:
    argv += ["--url", url]
spec = importlib.util.spec_from_file_location("insurer_disclosure_hero_probe", TARGET)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
probe.HERO_DIR = INSTALLED_HERO_DIR
raise SystemExit(probe.main(argv))
