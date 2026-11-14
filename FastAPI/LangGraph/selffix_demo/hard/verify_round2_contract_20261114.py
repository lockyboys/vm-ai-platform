"""실제 사고 답(job ca0a8c65 round2)을 고친 출력 검사기로 다시 판정한다 (2026-11-14, LuckyBoys 요청).

확인할 것
1) 예전 검사기가 거부한 round2/review_output.txt 를 지금 검사기는 통과시키는가(오류 목록이 비었는가).
2) 통과한다면 그 답의 전체 소스가 테트리스 채점 식 188개를 모두 맞추는가(사람 대신 기계로 확인).
LLM 호출 없음. 파일은 읽기만 하고, 원본 소스는 바꾸지 않는다.
"""
import json
import sys
import types
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
sys.path.insert(0, str(ROOT))
from FastAPI.LangGraph.multi_persona.review_contract import build_review_query, source_block, validate_review  # noqa: E402
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402

ROUND = ROOT / "harness/memory/source_reviews/job_ca0a8c65c6d244078ecd26e4a422eb59/round2"
text = (ROUND / "review_output.txt").read_text(encoding="utf-8")
answer = text[text.find("## 1. 전문가적 견해"):]  # CLI 로그 앞부분을 뺀 답 본문
candidate = ROUND / "tetris_engine_gemini.py"   # 2차 리뷰에 넣었던 입력 소스
query = build_review_query(str(candidate), candidate.read_text(encoding="utf-8"),
                           (ROUND / "feedback.txt").read_text(encoding="utf-8"))
errors = validate_review(answer, query)

code = source_block(answer[answer.find("## 3. 최종 수정 전체 소스 코드"):])
module = types.ModuleType("round2_answer")
exec(compile(code, "round2_answer", "exec"), module.__dict__)  # noqa: S102 - 채점용으로만 실행
cases, want = bs.cases("tetris_engine"), bs.expected("tetris_engine")
failing = [i for i, expr in enumerate(cases) if not bs.matches(bs.run_case(module, expr), want[i])]
print(json.dumps({"contract_errors_now": errors, "cases": len(cases), "failing_cases": failing},
                 ensure_ascii=False))
