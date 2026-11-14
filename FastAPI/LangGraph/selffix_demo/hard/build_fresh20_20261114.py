"""새 오류 20개(새 얽힌 10 + 처음 쓰는 한 줄 10) 시험 세트 생성기 (2026-11-14, LuckyBoys 요청).

"새로 만들어야 되는거 아냐 벌써 해 봤잖아" → 지난 시험(combo20·hard10·tangled10)에서 쓴 오류는 하나도 쓰지 않는다.
구성
- 얽힌 오류 10개: fresh20/<program>_mutations.py (새로 설계)
- 한 줄 오류 10개: 기존 오류 100개(_build/<program>_mutations.py) 중 지난 시험에서 안 쓴 것만, 분야마다 1개.
  분야 안에서는 찾기 어려운 것(혼자 넣었을 때 실패 식이 적은 것)부터 시도하고, 겹치거나 가려지면 다음 후보.
검증: 20개를 합친 파일에서 오류마다 실패 식이 1개 이상, 컴파일 성공. 어기면 중단(파일 안 씀).
재사용: 겹침·가려짐 처리 함수는 build_combo20_20261114.py 것을 그대로 쓴다(같은 규칙).
실행
  python FastAPI/LangGraph/selffix_demo/hard/build_fresh20_20261114.py          # dry-run: 검증만
  python FastAPI/LangGraph/selffix_demo/hard/build_fresh20_write_20261114.py    # 파일 생성(--write)
생성(이미 있으면 덮어쓰지 않음): fresh20/<program>_original.py, _gemini.py, _bugmap.json
"""
import importlib
import json
import sys
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

sys.path.insert(0, str(Path(config.PROJECT_ROOT)))
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402
from FastAPI.LangGraph.selffix_demo.hard.build_combo20_20261114 import (  # noqa: E402
    MAX_TRIES, _apply, _combine, _failing, _load)

HARD_DIR = Path(config.PROJECT_ROOT) / "FastAPI/LangGraph/selffix_demo/hard"
BUILD_DIR = HARD_DIR / "_build"
OUT_DIR = HARD_DIR / "fresh20"
AIS = ("gemini",)
# 지난 시험에서 쓴 한 줄 오류 번호(combo20 + hard10). 다시 쓰지 않는다.
USED_SINGLES = {
    "calc_engine": {6, 12, 23, 32, 41, 55, 67, 73, 84, 95, 51, 63, 71, 82, 92},
    "tetris_engine": {1, 12, 29, 32, 48, 52, 65, 73, 81, 93, 27, 45, 64, 90},
}


def build(program, write):
    ref = (BUILD_DIR / f"{program}_ref.py").read_text(encoding="utf-8")
    case_list = bs.cases(program)
    want = [bs.run_case(_load(ref), expr) for expr in case_list]
    tangled = [{"kind": "tangled", "no": f"N{m[0]}", "category": m[1], "function": m[2], "description": m[3],
                "pairs": m[4]}
               for m in importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard.fresh20.{program}_mutations").M]
    problems = []
    for bug in tangled:  # 새 얽힌 오류는 혼자 넣어도 드러나야 한다
        one = _apply(ref, bug["pairs"])
        if one is None:
            problems.append(f"{bug['no']} 정답 코드 조각이 1번이 아님")
        elif not _failing(one, case_list, want):
            problems.append(f"{bug['no']} 혼자 넣으면 드러나지 않음")
    if problems:
        raise SystemExit(f"{program}: {problems}")
    by_cat = {}
    for no, cat, func, desc, pairs in importlib.import_module(
            f"FastAPI.LangGraph.selffix_demo.hard._build.{program}_mutations").M:
        if no in USED_SINGLES[program]:
            continue
        one = _apply(ref, pairs)
        hardness = len(_failing(one, case_list, want)) if one is not None else 10 ** 6
        by_cat.setdefault(cat, []).append((hardness, no, {"kind": "single", "no": f"S{no}", "category": cat,
                                                          "function": func, "description": desc, "pairs": pairs}))
    queues = {cat: [c[2] for c in sorted(items, key=lambda x: (x[0], x[1]))] for cat, items in by_cat.items()}
    chosen, skipped = {}, []
    for cat in queues:
        while queues[cat]:
            cand = queues[cat].pop(0)
            if _combine(ref, tangled + list(chosen.values()) + [cand]) is not None:
                chosen[cat] = cand
                break
            skipped.append(f"{cand['no']}(겹침)")
    if _combine(ref, tangled) is None:
        raise SystemExit(f"{program}: 새 얽힌 오류끼리 겹침")
    for _ in range(MAX_TRIES):
        bugs = tangled + list(chosen.values())
        buggy = _combine(ref, bugs)
        buggy_fails = _failing(buggy, case_list, want)
        masked = []
        for bug in bugs:
            single = _failing(_apply(ref, bug["pairs"]), case_list, want)
            bug["single_fail_cases"] = len(single)
            bug["cases"] = sorted(single & buggy_fails)
            if not bug["cases"]:
                masked.append(bug)
        if not masked:
            break
        for bug in masked:
            if bug["kind"] == "tangled":
                raise SystemExit(f"{program}: 새 얽힌 오류 {bug['no']}가 다른 오류에 가려짐")
            cat = bug["category"]
            skipped.append(f"{bug['no']}(가려짐)")
            while queues[cat]:
                cand = queues[cat].pop(0)
                rest = [b for c, b in chosen.items() if c != cat]
                if _combine(ref, tangled + rest + [cand]) is not None:
                    chosen[cat] = cand
                    break
                skipped.append(f"{cand['no']}(겹침)")
            else:
                raise SystemExit(f"{program}: 분야 '{cat}'에 쓸 수 있는 후보가 없음")
    else:
        raise SystemExit(f"{program}: {MAX_TRIES}번 바꿔도 가려진 오류가 남음")
    compile(buggy, program, "exec")
    bugmap = [{k: b[k] for k in ("kind", "no", "category", "function", "description", "single_fail_cases", "cases")}
              for b in bugs]
    written = []
    if write:
        OUT_DIR.mkdir(exist_ok=True)
        targets = [OUT_DIR / f"{program}_original.py"] + [OUT_DIR / f"{program}_{ai}.py" for ai in AIS]
        existing = [p.name for p in targets if p.exists()]
        if existing:
            raise SystemExit(f"{program}: 이미 있는 파일은 덮어쓰지 않음: {existing}")
        for path in targets:
            path.write_text(buggy, encoding="utf-8")
            written.append(path.name)
        (OUT_DIR / f"{program}_bugmap.json").write_text(json.dumps(bugmap, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
        written.append(f"{program}_bugmap.json")
    return {"program": program, "bugs": len(bugs), "buggy_failing_cases": len(buggy_fails),
            "tangled": [f"{b['no']} {b['function']}({b['single_fail_cases']})" for b in bugs if b["kind"] == "tangled"],
            "singles": [f"{b['no']} {b['function']}({b['single_fail_cases']})" for b in bugs if b["kind"] == "single"],
            "skipped": skipped, "written": written}


def main():
    unknown = [a for a in sys.argv[1:] if a != "--write"]
    if unknown:  # 잘못된 입력: 모르는 인자
        raise SystemExit(f"알 수 없는 인자: {unknown} (허용: --write)")
    print(json.dumps([build(p, "--write" in sys.argv) for p in bs.PROGRAMS], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
