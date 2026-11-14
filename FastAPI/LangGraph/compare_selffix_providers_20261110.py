"""Gemini vs Ollama 자가 수정 결과 비교 (2026-11-10, LuckyBoys 요청: 계산기·테트리스 2건).

각 job의 result.json(검증 여부·시간·LLM 호출 수)과, 제안 소스(proposed.py)를 임시 폴더에 복사해
같은 테스트를 돌린 결과(통과/실패 수)를 표로 출력한다. 원본 소스는 바꾸지 않는다. LLM 호출 없음.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
# 2026-11-10 LuckyBoys 정정: 비교 대상은 ChatGPT(openai)·Claude. Ollama는 참고용으로 함께 표시.
JOBS = {
    # ChatGPT 1차는 401 키 오류, 2·3차는 temperature 400 오류 → 설정 수정 후 재실행한 job
    ("calculator", "openai"): "cb3e3d7278a0469a89273adb96d02411",
    ("tetris", "openai"): "b1019760bff04491bcde797d29df9b34",
    # Claude 1차(0b2d2ebe·86a33656)는 temperature 400 오류 → 수정 후 재실행한 job
    ("calculator", "claude"): "24a9715c95fb46b5b039240a82a9043f",
    ("tetris", "claude"): "2b1d6d67407d4cafbd3e515b9ce5c9c5",
    # Gemini 1·2차는 402 크레딧 소진 / 429 월 상한 → 상한 상향 후 재실행한 job
    ("calculator", "gemini"): "a750b05948694dc9b18347a15ead0a02",
    ("tetris", "gemini"): "db2687fba5634ac798c883ca41147265",
    # Ollama(8c5bfd7f·10cee30b)는 CPU 전용 서버에서 3590초 시간 초과 → 비교에서 제외
    # 노트북 터널(127.0.0.1:11435)로 재실행한 Ollama job (전용 CLI, num_ctx 8192)
    ("calculator", "ollama"): "b3bcbc53742c4c1db279c7b72d6a3208",
    ("tetris", "ollama"): "130c8cf0776c4b4389836eea09fc4bc8",
}
MODULES = {"calculator": ("calculator.py", "harness/tests/test_selffix_demo_calculator_20261110.py"),
           "tetris": ("tetris_core.py", "harness/tests/test_selffix_demo_tetris_20261110.py")}


def _test_proposal(proposed: Path, module_file: str, test_file: str) -> str:
    """임시 저장소에 제안 소스를 원래 모듈 이름으로 두고 같은 테스트를 돌린다(원본 미변경)."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "FastAPI/LangGraph/selffix_demo"
        pkg.mkdir(parents=True)
        shutil.copy(proposed, pkg / module_file)
        shutil.copy(ROOT / test_file, Path(tmp) / Path(test_file).name)
        done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               str(Path(tmp) / Path(test_file).name)],
                              cwd=tmp, capture_output=True, text=True, timeout=120,
                              env={"PYTHONPATH": tmp, "PATH": "/usr/bin:/bin"})
        last = (done.stdout.strip().splitlines() or ["?"])[-1]
        return last


def _recheck(job_dir: Path, program: str):
    """제안 파일이 없을 때: review.md의 3번 코드 블록을 새 계약 규칙으로 다시 검사하고 테스트로 채점한다.

    2026-11-10 계약 오탐 수정 이후, 이미 끝난 리뷰를 LLM 재호출 없이 다시 판정하기 위한 것이다.
    """
    from FastAPI.LangGraph.multi_persona.review_contract import (
        HEADINGS, build_review_query, source_block, validate_review)
    report = job_dir / "review.md"
    if not report.is_file():
        return None, "no report"
    module_file, test_file = MODULES[program]
    source = ROOT / "FastAPI/LangGraph/selffix_demo" / module_file
    text = report.read_text(encoding="utf-8")
    errors = validate_review(text, build_review_query(source, source.read_text(encoding="utf-8")))
    code = source_block(text.split(HEADINGS[2], 1)[-1]) if HEADINGS[2] in text else ""
    if not code:
        return errors, "no code block"
    candidate = job_dir / "recheck_proposed.py"
    candidate.write_text(code, encoding="utf-8")  # job 폴더 안에만 쓴다(원본 미변경)
    return errors, _test_proposal(candidate, module_file, test_file)


def main() -> None:
    rows = []
    for (program, provider), job_id in JOBS.items():
        job_dir = ROOT / "harness/memory/source_reviews" / ("job_" + job_id)
        result_path = job_dir / "result.json"
        if not result_path.is_file():
            rows.append({"program": program, "provider": provider, "state": "running"})
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        calls = re.search(r"페르소나=(\d+).*?LLM=(\d+)", result.get("output", ""))
        proposed = job_dir / "proposed.py"
        recheck_errors, recheck_tests = (None, None) if proposed.is_file() else _recheck(job_dir, program)
        rows.append({
            "program": program, "provider": provider, "state": result.get("state"),
            "verified": result.get("model_verified"), "seconds": result.get("elapsed_seconds"),
            "persona_calls": calls.group(1) if calls else None, "llm_calls": calls.group(2) if calls else None,
            "reasons": result.get("verification_reasons"),
            "proposal_tests": _test_proposal(proposed, *MODULES[program]) if proposed.is_file() else "no proposal",
            "recheck_contract_errors": recheck_errors, "recheck_tests": recheck_tests,
        })
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
