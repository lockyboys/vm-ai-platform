"""어려운 시험의 기존 AI 수정안을 새 'improve' 규칙으로 다시 적용해 보는 스크립트 (2026-11-11, LuckyBoys 요청).

- AI를 다시 부르지 않는다(비용 0). 이미 끝난 8개 job의 proposed.py를 그대로 쓴다.
- harness.mcp.tools.auto_apply.apply_with_rollback(policy="improve")를 그대로 호출한다
  = 실제 자가 수정 앱과 같은 코드로 '퇴행 없이 통과 수가 늘면 적용'을 확인한다.
- 대상은 hard/<program>_<ai>.py 사본뿐이다. *_original.py는 건드리지 않는다.
- 이미 전부 통과해 적용된 파일(현재 파일이 수정안과 같음)은 건너뛴다.
- 백업과 테스트 결과는 harness/memory/selffix_bench/reapply_<program>_<ai>/ 에 남는다.
"""
import hashlib
import json
import sys
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
sys.path.insert(0, str(ROOT))
from harness.mcp.tools import auto_apply  # noqa: E402

JOBS = {  # 2026-11-11 01:01 KST에 시작한 어려운 시험 job
    ("calc_engine", "gemini"): "06c76ff243644011a15cdc5427d68f76",
    ("calc_engine", "openai"): "e6749ac2480e41a19ca6851ea88f265a",
    ("calc_engine", "claude"): "ed2a50bee7b640579d8cc805f2e24982",
    ("calc_engine", "ollama"): "7867678b350a40cda802232bba89686a",
    ("tetris_engine", "gemini"): "8f91129a444f458a9c54c5106e361ef9",
    ("tetris_engine", "openai"): "35ee96f3778b4f0c9234fddba3c8961f",
    ("tetris_engine", "claude"): "82ea487ca61c4409b9fa74a45318112f",
    ("tetris_engine", "ollama"): "10ee4d8b84c140d98d81feaa59c885e4",
}


def main():
    rows = []
    for (program, ai), job_id in JOBS.items():
        source = ROOT / f"FastAPI/LangGraph/selffix_demo/hard/{program}_{ai}.py"
        proposed = ROOT / f"harness/memory/source_reviews/job_{job_id}/proposed.py"
        if not proposed.is_file():
            rows.append({"program": program, "ai": ai, "skipped": "no proposal"})
            continue
        if source.read_bytes() == proposed.read_bytes():
            rows.append({"program": program, "ai": ai, "skipped": "already applied"})
            continue
        work = ROOT / f"harness/memory/selffix_bench/reapply_{program}_{ai}"
        work.mkdir(parents=True, exist_ok=True)
        state = auto_apply.apply_with_rollback(
            source, proposed, work, hashlib.sha256(source.read_bytes()).hexdigest(),
            [f"harness/tests/selffix_hard/bench_{program}_{ai}.py"], 900, ROOT, policy="improve")
        (work / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        rows.append({"program": program, "ai": ai,
                     **{k: state.get(k) for k in ("applied", "partial", "rolled_back", "reason",
                                                  "tests_passed_before", "tests_passed_after", "tests_total")}})
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
