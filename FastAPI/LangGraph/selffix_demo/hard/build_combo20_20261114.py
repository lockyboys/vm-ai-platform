"""오류 20개(얽힌 10 + 한 줄 10) 시험 세트 생성기 (2026-11-14, LuckyBoys 결정: "합쳐서 각 20개").

구성
- 얽힌 오류 10개: tangled10/<program>_mutations.py 전부(짝·번지는·순서 오류).
- 한 줄 오류 10개: 기존 오류 100개(_build/<program>_mutations.py)에서 분야마다 1개.
  분야 안에서는 '혼자 넣었을 때 실패 식이 가장 적은 것(=찾기 어려운 것)'부터 시도하고,
  얽힌 오류와 같은 코드를 건드려 적용이 안 되거나(조각이 1번이 아님), 20개를 합친 파일에서
  다른 오류에 가려 드러나지 않으면 같은 분야의 다음 후보로 바꾼다.
검증: 20개 모두 합친 파일에서 오류마다 실패 식이 1개 이상, 컴파일 성공.
실행
  python FastAPI/LangGraph/selffix_demo/hard/build_combo20_20261114.py          # dry-run
  python FastAPI/LangGraph/selffix_demo/hard/build_combo20_write_20261114.py    # 파일 생성(--write)
생성 파일(이미 있으면 덮어쓰지 않음): combo20/<program>_original.py, _gemini.py, _bugmap.json
"""
import importlib
import json
import sys
import types
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

sys.path.insert(0, str(Path(config.PROJECT_ROOT)))
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402

HARD_DIR = Path(config.PROJECT_ROOT) / "FastAPI/LangGraph/selffix_demo/hard"
BUILD_DIR = HARD_DIR / "_build"
OUT_DIR = HARD_DIR / "combo20"
AIS = ("gemini",)
MAX_TRIES = 30  # 가려짐 때문에 후보를 바꾸는 최대 횟수(무한 반복 방지)


def _load(source):
    """소스 문자열을 새 모듈로 실행한다. 실패하면 예외 객체를 돌려준다."""
    module = types.ModuleType("target")
    try:
        exec(compile(source, "target", "exec"), module.__dict__)  # noqa: S102 - 생성기 내부 소스만 실행
    except Exception as exc:  # noqa: BLE001
        return exc
    return module


def _failing(source, case_list, want):
    """기대값과 다른 식 번호 집합(모듈 로드 실패면 전부)."""
    module = _load(source)
    if isinstance(module, Exception):
        return set(range(len(case_list)))
    return {i for i, expr in enumerate(case_list) if not bs.matches(bs.run_case(module, expr), want[i])}


def _apply(source, pairs):
    """조각을 순서대로 바꾼다. 조각이 정확히 1번이 아니면 None(적용 불가 = 다른 오류와 겹침)."""
    for old, new in pairs:
        if source.count(old) != 1:
            return None
        source = source.replace(old, new)
    return source


def _combine(ref, bugs):
    """오류 목록을 차례로 넣은 소스(겹치면 None)."""
    source = ref
    for bug in bugs:
        source = _apply(source, bug["pairs"])
        if source is None:
            return None
    return source


def build(program, write):
    ref = (BUILD_DIR / f"{program}_ref.py").read_text(encoding="utf-8")
    case_list = bs.cases(program)
    want = [bs.run_case(_load(ref), expr) for expr in case_list]
    tangled = [{"kind": "tangled", "no": f"T{m[0]}", "category": m[1], "function": m[2], "description": m[3],
                "pairs": m[4]}
               for m in importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard.tangled10.{program}_mutations").M]
    singles = importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard._build.{program}_mutations").M
    # 분야별 후보: 혼자 넣었을 때 실패 식 수가 적은 순서(어려운 것부터)
    by_cat = {}
    for no, cat, func, desc, pairs in singles:
        one = _apply(ref, pairs)
        hardness = len(_failing(one, case_list, want)) if one is not None else 10 ** 6
        by_cat.setdefault(cat, []).append((hardness, no, {"kind": "single", "no": f"S{no}", "category": cat,
                                                          "function": func, "description": desc, "pairs": pairs}))
    queues = {cat: [c[2] for c in sorted(items, key=lambda x: (x[0], x[1]))] for cat, items in by_cat.items()}
    chosen, skipped = {}, []
    for cat in queues:  # 1차: 겹치지 않는 첫 후보
        while queues[cat]:
            cand = queues[cat].pop(0)
            if _combine(ref, tangled + list(chosen.values()) + [cand]) is not None:
                chosen[cat] = cand
                break
            skipped.append(f"{cand['no']}(겹침)")
    for _ in range(MAX_TRIES):  # 2차: 가려진 오류가 있으면 그 분야 후보 교체
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
                raise SystemExit(f"{program}: 얽힌 오류 {bug['no']}가 가려짐(한 줄 오류 조합을 바꿔도 해결 안 됨)")
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
            "singles": [f"{b['no']} {b['function']}({b['single_fail_cases']})" for b in bugs if b["kind"] == "single"],
            "skipped": skipped, "written": written}


def main():
    unknown = [a for a in sys.argv[1:] if a != "--write"]
    if unknown:  # 잘못된 입력: 모르는 인자
        raise SystemExit(f"알 수 없는 인자: {unknown} (허용: --write)")
    print(json.dumps([build(p, "--write" in sys.argv) for p in bs.PROGRAMS], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
