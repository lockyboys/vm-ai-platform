"""실제 사고 리뷰 답변으로 새 계약 검사를 재확인하는 1회성 검증 스크립트 (2026-11-02).

목적: job 0fded59b...가 남긴 multi_persona_tools.review.md(haness -> harness 오수정 포함)를
      수정된 validate_review에 다시 넣어, 이제는 "존재하지 않는 import 대상" 오류가 나는지 확인한다.
원칙: LLM·대상 소스 실행 없음. 파일 읽기와 ast 분석만 한다.
"""
import json
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)
from FastAPI.LangGraph.multi_persona.review_contract import build_review_query, validate_review

ROOT = Path(config.PROJECT_ROOT)
# 원본: 수정 직전 백업(haness 경로를 그대로 가진 소스)
ORIGINAL = ROOT / "harness/backups/review_selffix_20261102/harness/mcp/tools/multi_persona_tools.py"
# 사고 당시 LLM 답변 전문
REVIEW = ROOT / "harness/mcp/tools/multi_persona_tools.review.md"


def main() -> None:
    query = build_review_query(ORIGINAL, ORIGINAL.read_text(encoding="utf-8"))
    errors = validate_review(REVIEW.read_text(encoding="utf-8"), query)
    print(json.dumps({"review": str(REVIEW.relative_to(ROOT)), "errors": errors,
                      "rejected": any("harness.mcp.tools.multi_persona_tools" in e for e in errors)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
