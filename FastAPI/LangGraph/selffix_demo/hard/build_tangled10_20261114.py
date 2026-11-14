"""'얽힌 오류' 10개 시험 세트 생성기 (2026-11-14, LuckyBoys 요청: "복잡하게 얽히게 짜 오류를").

무엇을 만드나
- 오류 정의: tangled10/<program>_mutations.py (짝 오류·번지는 오류·순서 오류, 오류마다 여러 곳을 바꿈)
- 채점 식·정답 구현: 기존 것(_build/<program>_cases_src.py, _build/<program>_ref.py) 그대로.
- 검증(하나라도 어기면 중단)
  1) 오류 하나만 넣어도 실패하는 채점 식이 1개 이상(드러나지 않는 오류 금지)
  2) 10개를 모두 넣은 파일에서도 오류마다 실패 식이 1개 이상(다른 오류에 가려짐 금지)
  3) 얽힘 확인: 오류마다 '한쪽만 고친' 경우(조각 하나만 정답으로 되돌림)에 결함 파일보다 새로 깨지는
     식이 있는지 센다(regress_if_partial). 0이면 얽힘이 약한 오류라는 뜻(보고만 하고 중단하지 않음).
실행
  python FastAPI/LangGraph/selffix_demo/hard/build_tangled10_20261114.py          # dry-run: 검증 결과만 출력
  python FastAPI/LangGraph/selffix_demo/hard/build_tangled10_write_20261114.py    # 파일 생성(--write)
생성 파일(이미 있으면 덮어쓰지 않고 중단, 일반 지침 7)
  tangled10/<program>_original.py, tangled10/<program>_gemini.py, tangled10/<program>_bugmap.json
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
OUT_DIR = HARD_DIR / "tangled10"
AIS = ("gemini",)  # 이번 요청은 Gemini만. 다른 AI가 필요하면 여기에 이름을 더한다.


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


def _apply(source, pairs, label):
    """조각을 순서대로 바꾼다. 바꿀 정답 코드는 그 시점에 정확히 1번만 있어야 한다(겹침 금지)."""
    for old, new in pairs:
        if source.count(old) != 1:
            raise SystemExit(f"{label}: 정답 코드 조각이 1번이 아님({source.count(old)}번): {old!r}")
        source = source.replace(old, new)
    return source


def build(program, write):
    ref = (BUILD_DIR / f"{program}_ref.py").read_text(encoding="utf-8")
    case_list = bs.cases(program)
    want = [bs.run_case(_load(ref), expr) for expr in case_list]
    mutations = importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard.tangled10.{program}_mutations").M
    if sorted(m[0] for m in mutations) != list(range(1, 11)):
        raise SystemExit(f"{program}: 오류 번호는 1..10 이어야 함")
    buggy = ref
    for no, _cat, _func, _desc, pairs in mutations:
        buggy = _apply(buggy, pairs, f"{program} #{no}(합치기)")
    compile(buggy, program, "exec")
    buggy_fails = _failing(buggy, case_list, want)
    bugmap, problems = [], []
    for no, cat, func, desc, pairs in mutations:
        single = _failing(_apply(ref, pairs, f"{program} #{no}"), case_list, want)
        visible = sorted(single & buggy_fails)
        if not single:
            problems.append(f"#{no} 혼자 넣으면 드러나지 않음")
        elif not visible:
            problems.append(f"#{no} 다른 오류에 가려짐")
        # 얽힘 확인: 이 오류의 조각 하나만 정답으로 되돌린(=한쪽만 고친) 결함 파일에서 새로 깨지는 식 수
        partial = []
        if len(pairs) > 1:
            for keep in range(len(pairs)):
                others = [p for k, p in enumerate(pairs) if k != keep]
                # 조각 keep만 정답으로 남기려면: 정답에 다른 오류 전부 + 이 오류의 나머지 조각만 넣는다.
                try:
                    source = ref
                    for n2, _c, _f, _d, p2 in mutations:
                        source = _apply(source, others if n2 == no else p2, f"{program} #{n2}(부분)")
                except SystemExit:
                    partial.append(None)  # 자리표시 조각 등으로 한쪽만 되돌릴 수 없는 경우
                    continue
                partial.append(len(_failing(source, case_list, want) - buggy_fails))
        bugmap.append({"no": no, "category": cat, "function": func, "description": desc,
                       "sites": len(pairs), "single_fail_cases": len(single), "cases": visible,
                       "regress_if_partial": partial})
    if problems:
        raise SystemExit(f"{program}: {problems}")
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
    return {"program": program, "cases": len(case_list), "buggy_failing_cases": len(buggy_fails),
            "bugs": [{k: b[k] for k in ("no", "function", "sites", "single_fail_cases", "regress_if_partial")}
                     | {"visible": len(b["cases"])} for b in bugmap],
            "written": written}


def main():
    unknown = [a for a in sys.argv[1:] if a != "--write"]
    if unknown:  # 잘못된 입력: 모르는 인자
        raise SystemExit(f"알 수 없는 인자: {unknown} (허용: --write)")
    print(json.dumps([build(p, "--write" in sys.argv) for p in bs.PROGRAMS], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
