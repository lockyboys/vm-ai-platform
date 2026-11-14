"""새 오류 20개(fresh20) 결과를 오류별로 채점하고, 무작위 입력으로 과적합을 점검한다 (2026-11-14, LuckyBoys 요청).

1) 오류별 채점: fresh20/<program>_bugmap.json 의 오류마다 채점 식(cases)이 모두 정답과 같으면 '고침'.
2) 과적합 점검(차분 시험): diff_check_20261111.py의 무작위 입력 생성기(고정 seed)로 정답 구현과
   고쳐진 파일을 비교한다. 채점 식에 없는 입력이라 시험 식만 외워서는 통과할 수 없다.
LLM 호출 없음, 파일은 읽기만 한다.
"""
import json
import random
import sys
import types
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

sys.path.insert(0, str(Path(config.PROJECT_ROOT)))
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402
from FastAPI.LangGraph.selffix_demo.hard import diff_check_20261111 as dc  # noqa: E402

HARD = Path(config.PROJECT_ROOT) / "FastAPI/LangGraph/selffix_demo/hard"


def _load(path):
    module = types.ModuleType(path.stem)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)  # noqa: S102
    return module


def grade(program, inputs):
    module = _load(HARD / "fresh20" / f"{program}_gemini.py")
    cases, want = bs.cases(program), bs.expected(program)
    rows = []
    for bug in json.loads((HARD / "fresh20" / f"{program}_bugmap.json").read_text(encoding="utf-8")):
        fails = [i for i in bug["cases"] if not bs.matches(bs.run_case(module, cases[i]), want[i])]
        rows.append({"no": bug["no"], "function": bug["function"], "fixed": not fails, "failing": fails})
    diff = dc.check(program, f"fresh20/{program}_gemini", _load(HARD / "_build" / f"{program}_ref.py"), inputs)
    return {"program": program, "fixed": sum(r["fixed"] for r in rows), "bugs": len(rows),
            "not_fixed": [r for r in rows if not r["fixed"]],
            "diff_inputs": diff["inputs"], "diff_mismatches": diff["mismatches"],
            "diff_by_function": {k: v for k, v in diff["by_function"].items()}}


if __name__ == "__main__":
    rng = random.Random(dc.SEED)
    inputs = {"calc_engine": dc.calc_inputs(rng), "tetris_engine": dc.tetris_inputs(rng)}
    print(json.dumps([grade(p, inputs[p]) for p in bs.PROGRAMS], ensure_ascii=False, indent=1))
