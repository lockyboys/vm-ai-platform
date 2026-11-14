"""hard2 자가 수정 시험 세트 생성·검증기 (2026-11-11, LuckyBoys 승인: 연쇄·조건부·미묘한 오류 100건씩).

실행: python FastAPI/LangGraph/selffix_demo/hard2/build_hard2.py [--write-targets] [--program=calc_engine]
  기본(dry-run): 검증만 하고 _build/ 의 기대값·채점 식·오류 지도·체크리스트·커버리지만 쓴다.
  --write-targets: AI별 대상 파일(<program>_<ai>.py)과 보존용 원본(<program>_original.py)을 hard2/ 에 쓴다.
                   이미 있으면 덮어쓰지 않고 중단한다(자동 수정 결과 보존, 일반 지침 7).
  --program=<이름>: 그 프로그램만 처리(없으면 오류 파일이 있는 프로그램 전부).

기존 hard(FastAPI/LangGraph/selffix_demo/hard)는 건드리지 않는다. 정답 소스만 hard/_build/<program>_ref.py 를 읽어 쓴다
(정답을 두 벌 두면 어긋날 수 있어 한 곳만 원본으로 삼는다).

hard 대비 강화한 검증
1) 오류마다 '전용 식' 1개 의무: 그 오류 하나만 넣으면 실패하고, 다른 오류 99개를 각각 하나만 넣었을 때는 통과해야 한다.
2) 종류(kind) 4가지: subtle(미묘) / conditional(조건부) / chain_spread(연쇄-번짐) / chain_mask(연쇄-가림).
   - chain_mask: 100개를 모두 넣은 파일에서는 '가리는 오류(mask_by)' 때문에 전용 식이 통과(가려짐)하고,
     가리는 오류만 되돌리면 실패(드러남)해야 한다. 즉 A를 고쳐야 B가 드러나는 오류.
   - 그 밖의 종류: 100개를 모두 넣은 파일에서도 전용 식이 실패해야 한다(뜻하지 않은 가림 금지).
3) 어려운 영역 체크리스트: 체크리스트의 모든 영역에 오류가 1개 이상, 모든 오류가 영역 1개 이상.
4) 정답 소스 라인 커버리지 100%: 채점 식 전체(전용 식 + 보충 식)로 정답 소스의 모든 문장을 실행한다.
   도달 불가능한 문장은 오류 파일의 UNREACHABLE 에 '정확한 코드 조각 + 이유'로 적어야만 제외된다
   (LuckyBoys 확인 2026-11-11: apply_top의 malformed expression 1줄 제외 후 100%).
   분기 커버리지는 측정하지 않는다 → 결과에 '미확인'으로 적는다.
"""
import ast
import importlib.util
import json
import sys
import types
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
sys.path.insert(0, str(ROOT))
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402  채점 실행·비교 규칙은 hard와 동일하게 공유

HARD2_DIR = ROOT / "FastAPI/LangGraph/selffix_demo/hard2"
BUILD_DIR = HARD2_DIR / "_build"
REF_DIR = ROOT / "FastAPI/LangGraph/selffix_demo/hard/_build"  # 정답 소스 원본 위치(hard와 공유, 읽기만)
AIS = ("gemini", "openai", "claude", "ollama")
KINDS = ("subtle", "conditional", "chain_spread", "chain_mask")
REF_FILENAME = "<hard2_ref>"  # 커버리지 추적용 가짜 파일 이름(정답 소스 프레임만 골라내기 위해)


class BuildError(Exception):
    """검증 실패. args[0]에 사람이 읽을 오류 목록(list[str])을 담는다."""


# ---------------------------------------------------------------- 오류 정의 읽기·형식 검증
def load_spec(program):
    """_build/<program>_mutations2.py 를 파일 경로로 읽는다(패키지 __init__ 유무와 무관하게). 없으면 None."""
    path = BUILD_DIR / f"{program}_mutations2.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"hard2_{program}_mutations2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_spec(bugs, checklist):
    """오류 목록 형식 검증. 문제가 있으면 BuildError(문제 목록)."""
    problems = []
    numbers = [b.get("no") for b in bugs]
    if sorted(n for n in numbers if isinstance(n, int)) != list(range(1, 101)) or len(numbers) != 100:
        problems.append("오류 번호는 1..100 이 정확히 한 번씩이어야 함")
    known = set(numbers)
    used_areas = set()
    for b in bugs:
        label = f"#{b.get('no')}"
        if b.get("kind") not in KINDS:
            problems.append(f"{label}: kind는 {KINDS} 중 하나여야 함")
        if not isinstance(b.get("case"), str) or not b["case"].strip():
            problems.append(f"{label}: 전용 식(case)이 없음")
        pairs = b.get("pairs")
        if not pairs or not all(isinstance(p, tuple) and len(p) == 2 and p[0] != p[1] for p in pairs):
            problems.append(f"{label}: pairs는 (정답 조각, 오류 조각) 튜플 목록이어야 하고 둘이 달라야 함")
        hard = b.get("hard") or []
        if not hard:
            problems.append(f"{label}: 어려운 영역(hard)이 비어 있음")
        for area in hard:
            if area not in checklist:
                problems.append(f"{label}: 체크리스트에 없는 영역 '{area}'")
        used_areas.update(hard)
        mask_by = b.get("mask_by")
        if b.get("kind") == "chain_mask":
            if mask_by not in known or mask_by == b.get("no"):
                problems.append(f"{label}: chain_mask는 다른 오류 번호 mask_by가 필요함")
        elif mask_by is not None:
            problems.append(f"{label}: mask_by는 chain_mask에서만 쓴다")
    missing_areas = sorted(set(checklist) - used_areas)
    if missing_areas:
        problems.append(f"오류가 하나도 없는 체크리스트 영역: {missing_areas}")
    if problems:
        raise BuildError(problems)


# ---------------------------------------------------------------- 소스 조작·실행
def apply_pairs(source, pairs, label):
    """정답 조각을 오류 조각으로 바꾼다. 조각은 바꾸는 시점에 정확히 1번만 있어야 한다(겹침·모호함 금지)."""
    for old, new in pairs:
        count = source.count(old)
        if count != 1:
            raise BuildError([f"{label}: 정답 조각이 {count}번 나옴(1번이어야 함): {old!r}"])
        source = source.replace(old, new)
    return source


def revert_pairs(source, pairs, label):
    """apply_pairs의 반대(가림 확인용: 가리는 오류만 되돌린다). 오류 조각도 1번만 있어야 한다."""
    for old, new in reversed(pairs):
        count = source.count(new) if new else 0
        if count != 1:
            raise BuildError([f"{label}: 되돌릴 오류 조각이 {count}번 나옴(1번이어야 함): {new!r}"])
        source = source.replace(new, old)
    return source


def load_module(source, filename="target"):
    """소스 문자열을 새 모듈로 실행한다. 실패하면 예외 객체를 돌려준다(결함 소스는 import부터 깨질 수 있음)."""
    module = types.ModuleType("target")
    try:
        exec(compile(source, filename, "exec"), module.__dict__)  # noqa: S102 - 생성기 내부 소스만 실행
    except Exception as exc:  # noqa: BLE001
        return exc
    return module


def run_all(module, exprs):
    """식 목록 실행 결과. 모듈 로드가 실패했으면 모든 식을 ('raises', 'LoadError')로 본다."""
    if isinstance(module, Exception):
        return [("raises", "LoadError")] * len(exprs)
    return [bs.run_case(module, expr) for expr in exprs]


# ---------------------------------------------------------------- 라인 커버리지(외부 패키지 없이 sys.settrace)
def executable_lines(source):
    """정답 소스의 실행 가능한 문장 시작 줄 번호(docstring 문장은 제외)."""
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docstrings.add(first.lineno)
    return {node.lineno for node in ast.walk(tree) if isinstance(node, ast.stmt)} - docstrings


def line_coverage(source, exprs):
    """정답 소스를 로드하고 식을 모두 실행하면서 실행된 줄을 모은다."""
    hit = set()

    def tracer(frame, event, _arg):
        # 정답 소스 프레임만 추적한다(채점 식·bench_support 프레임은 무시).
        if frame.f_code.co_filename != REF_FILENAME:
            return None
        if event == "line":
            hit.add(frame.f_lineno)
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        module = load_module(source, REF_FILENAME)
        run_all(module, exprs)
    finally:
        sys.settrace(previous)
    return hit


def unreachable_lines(source, unreachable):
    """UNREACHABLE {코드 조각: 이유} → {줄 번호: 이유}. 조각은 정답 소스에 정확히 1번 있어야 한다."""
    lines, problems = {}, []
    for snippet, reason in unreachable.items():
        if source.count(snippet) != 1:
            problems.append(f"UNREACHABLE 조각이 정답 소스에 1번이 아님: {snippet!r}")
            continue
        lines[source[: source.index(snippet)].count("\n") + 1] = reason
    if problems:
        raise BuildError(problems)
    return lines


# ---------------------------------------------------------------- 본 검증
def build(program, write_targets=False, write_outputs=True):
    spec = load_spec(program)
    if spec is None:
        return {"program": program, "status": "미작성", "detail": f"_build/{program}_mutations2.py 없음"}
    bugs, checklist = spec.BUGS, spec.CHECKLIST
    validate_spec(bugs, checklist)
    ref = (REF_DIR / f"{program}_ref.py").read_text(encoding="utf-8")
    dedicated = [b["case"] for b in bugs]
    cover = list(getattr(spec, "COVER", []))
    all_cases = dedicated + cover
    want = run_all(load_module(ref), all_cases)
    problems = []

    # 1) 오류 하나씩 넣은 결과(전용 식만) → 자기 오류는 잡고, 다른 오류에는 통과해야 '전용'
    single = {}
    for b in bugs:
        try:
            single[b["no"]] = run_all(load_module(apply_pairs(ref, b["pairs"], f"#{b['no']}")), dedicated)
        except BuildError as exc:
            problems.extend(exc.args[0])
    if problems:  # 조각 자체가 틀리면 아래 검사는 의미가 없다
        raise BuildError(problems)
    for i, b in enumerate(bugs):
        if bs.matches(single[b["no"]][i], want[i]):
            problems.append(f"#{b['no']} {b['func']}: 전용 식이 자기 오류를 못 잡음 (기대 {want[i]})")
        others = [o["no"] for o in bugs if o["no"] != b["no"] and not bs.matches(single[o["no"]][i], want[i])]
        if others:
            problems.append(f"#{b['no']} {b['func']}: 전용 식이 다른 오류 {others} 에도 실패(전용 아님)")

    # 2) 100개를 모두 넣은 결함 소스 + 가림/드러남 검사
    buggy = ref
    for b in bugs:
        buggy = apply_pairs(buggy, b["pairs"], f"#{b['no']}(합칠 때)")
    compile(buggy, program, "exec")  # 문법 오류면 여기서 바로 실패
    full = run_all(load_module(buggy), dedicated)
    by_no = {b["no"]: b for b in bugs}
    mask_report = []
    for i, b in enumerate(bugs):
        visible = not bs.matches(full[i], want[i])
        if b["kind"] == "chain_mask":
            masker = by_no[b["mask_by"]]
            unmasked_src = revert_pairs(buggy, masker["pairs"], f"#{b['no']} mask_by #{masker['no']}")
            revealed = not bs.matches(run_all(load_module(unmasked_src), [b["case"]])[0], want[i])
            mask_report.append({"no": b["no"], "mask_by": masker["no"], "masked_in_full": not visible,
                                "revealed_after_fix": revealed})
            if visible:
                problems.append(f"#{b['no']}: chain_mask인데 전체 파일에서 가려지지 않음 (결과 {full[i]})")
            if not revealed:
                problems.append(f"#{b['no']}: #{masker['no']}를 되돌려도 드러나지 않음")
        elif not visible:
            problems.append(f"#{b['no']} {b['func']}: 전체 파일에서 다른 오류에 가려짐(chain_mask로 표시 안 됨)")

    # 3) 라인 커버리지(정답 소스, 채점 식 전체)
    executable = executable_lines(ref)
    excluded = unreachable_lines(ref, getattr(spec, "UNREACHABLE", {}))
    hit = line_coverage(ref, all_cases)
    wrongly_excluded = sorted(set(excluded) & hit)
    if wrongly_excluded:
        problems.append(f"UNREACHABLE로 적었지만 실제로 실행된 줄: {wrongly_excluded}")
    missed = sorted(executable - hit - set(excluded))
    if missed:
        problems.append(f"정답 소스에서 실행되지 않은 줄: {missed}")
    if problems:
        raise BuildError(problems)

    covered = len(executable - set(excluded))
    kinds = {k: sum(b["kind"] == k for b in bugs) for k in KINDS}
    areas = {area: [b["no"] for b in bugs if area in b["hard"]] for area in checklist}
    bugmap = [{"no": b["no"], "kind": b["kind"], "function": b["func"], "description": b["desc"],
               "hard": b["hard"], "mask_by": b.get("mask_by"), "cases": [i]} for i, b in enumerate(bugs)]
    if write_outputs:
        out = {
            f"{program}_cases.json": all_cases,
            f"{program}_expected.json": [[kind, value if kind == "raises" else repr(value)] for kind, value in want],
            f"{program}_bugmap.json": bugmap,
            f"{program}_checklist.json": {area: {"description": checklist[area], "bugs": areas[area]} for area in checklist},
            f"{program}_coverage.json": {"kind": "line(sys.settrace)", "executable": len(executable),
                                         "excluded_unreachable": {str(n): r for n, r in sorted(excluded.items())},
                                         "covered": covered, "percent": 100.0, "branch": "미확인"},
        }
        for name, data in out.items():
            (BUILD_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    written = []
    if write_targets:
        targets = [HARD2_DIR / f"{program}_original.py"] + [HARD2_DIR / f"{program}_{ai}.py" for ai in AIS]
        existing = [p.name for p in targets if p.exists()]
        if existing:  # 자동 수정 결과를 실수로 지우지 않기 위해 절대 덮어쓰지 않는다
            raise BuildError([f"{program}: 이미 있는 대상 파일은 덮어쓰지 않음: {existing}"])
        for path in targets:
            path.write_text(buggy, encoding="utf-8")
            written.append(path.name)
    return {"program": program, "status": "ok", "bugs": len(bugs), "kinds": kinds,
            "dedicated_cases": len(dedicated), "cover_cases": len(cover),
            "line_coverage": f"{covered}/{covered} (100%, 제외 {len(excluded)}줄)", "branch_coverage": "미확인",
            "masks": mask_report, "checklist_areas": len(checklist),
            "buggy_failing_dedicated": sum(not bs.matches(full[i], want[i]) for i in range(len(bugs))),
            "written": written}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    write_targets = "--write-targets" in argv
    chosen = [a.split("=", 1)[1] for a in argv if a.startswith("--program=")]
    unknown = set(chosen) - set(bs.PROGRAMS)
    if unknown:  # 잘못된 입력: 없는 프로그램 이름
        raise SystemExit(f"알 수 없는 프로그램: {sorted(unknown)} (허용: {list(bs.PROGRAMS)})")
    results = []
    for program in chosen or bs.PROGRAMS:
        try:
            results.append(build(program, write_targets))
        except BuildError as exc:
            results.append({"program": program, "status": "실패", "problems": exc.args[0]})
    print(json.dumps(results, ensure_ascii=False, indent=1))
    return results


if __name__ == "__main__":
    main()
