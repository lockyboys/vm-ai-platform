"""combo20 2회차 시험 사본 만들기 (2026-11-14, LuckyBoys 요청 "시도 해봐").

목적: 앱 수정(검사 거부 시 재시도, 라운드별 temperature 0.4→0.2→0.0, 최대 3라운드) 후 오류 20개를
      처음부터 다시 고치게 해 1회차(<program>_gemini.py, 결과 보존)와 비교한다.
동작: <program>_original.py(결함 원본)를 <program>_gemini_run2.py로 복사한다. 이미 있으면 덮어쓰지 않는다.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
for program in ("calc_engine", "tetris_engine"):
    target = HERE / f"{program}_gemini_run2.py"
    if target.exists():
        raise SystemExit(f"이미 있어 덮어쓰지 않음: {target.name}")
    target.write_bytes((HERE / f"{program}_original.py").read_bytes())
    print("created", target.name)
