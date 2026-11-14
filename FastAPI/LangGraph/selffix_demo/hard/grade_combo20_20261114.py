"""오류 20개 시험 결과를 오류별로 채점한다 (2026-11-14, LuckyBoys 요청: "어떤 오류를 어떻게 고쳤는지").

- 대상: combo20/<program>_gemini.py (자동 수정이 반영된 현재 파일)
- 기준: combo20/<program>_bugmap.json 의 오류별 채점 식(cases)이 모두 정답과 같으면 '고침'.
- 함께 출력: 오류마다 남은 실패 식(식·실제값·기대값)과, 고친 코드가 정답 구현과 같은 줄인지 확인할 수 있게
  결함 코드 조각이 아직 남아 있는지(still_has_bug_code)도 본다(조각이 남아 있어도 다르게 고쳤을 수 있음).
LLM 호출 없음, 파일은 읽기만 한다.
"""
import importlib
import json
import sys
import types
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

sys.path.insert(0, str(Path(config.PROJECT_ROOT)))
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402

HARD = Path(config.PROJECT_ROOT) / "FastAPI/LangGraph/selffix_demo/hard"


def _load(path):
    module = types.ModuleType(path.stem)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)  # noqa: S102
    return module


def _bug_pairs(program):
    """오류 번호(T1.., S12..) → 결함 코드 조각 목록."""
    pairs = {}
    for m in importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard.tangled10.{program}_mutations").M:
        pairs[f"T{m[0]}"] = m[4]
    for m in importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard._build.{program}_mutations").M:
        pairs[f"S{m[0]}"] = m[4]
    return pairs


def grade(program):
    target = HARD / "combo20" / f"{program}_gemini.py"
    source = target.read_text(encoding="utf-8")
    module = _load(target)
    cases, want = bs.cases(program), bs.expected(program)
    pairs = _bug_pairs(program)
    rows = []
    for bug in json.loads((HARD / "combo20" / f"{program}_bugmap.json").read_text(encoding="utf-8")):
        fails = []
        for i in bug["cases"]:
            got = bs.run_case(module, cases[i])
            if not bs.matches(got, want[i]):
                fails.append({"case": i, "expr": cases[i][:160], "got": repr(got)[:120], "want": repr(want[i])[:120]})
        leftover = [new[:80] for _old, new in pairs[bug["no"]] if new.strip() and new in source]
        rows.append({"no": bug["no"], "kind": bug["kind"], "function": bug["function"],
                     "fixed": not fails, "failing": fails, "still_has_bug_code": leftover})
    total = [i for i in range(len(cases)) if not bs.matches(bs.run_case(module, cases[i]), want[i])]
    return {"program": program, "fixed": sum(r["fixed"] for r in rows), "bugs": len(rows),
            "all_failing_cases": total, "rows": rows}


if __name__ == "__main__":
    print(json.dumps([grade(p) for p in bs.PROGRAMS], ensure_ascii=False, indent=1))
