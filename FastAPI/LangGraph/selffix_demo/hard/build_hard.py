"""어려운 자가 수정 시험 세트 생성·검증기 (2026-11-11, LuckyBoys 요청: 프로그램별 오류 100개, 분야별 고르게).

실행: python FastAPI/LangGraph/selffix_demo/hard/build_hard.py [--write-targets]
  기본(dry-run): 검증만 하고 _build/의 기대값·오류 지도만 다시 쓴다(AI 대상 파일은 건드리지 않음).
  --write-targets: AI별 대상 파일(<program>_<ai>.py)과 보존용 원본(<program>_original.py)을 새로 쓴다.
                   이미 있으면 덮어쓰지 않고 중단한다(자동 수정 결과를 실수로 지우지 않기 위해).
  --rewrite=<program>: 정답 소스 docstring 보강 등으로 결함 소스가 바뀌었을 때 그 프로그램만 다시 쓴다
                   (2026-11-11 추가). AI 사본이 하나라도 기존 원본과 다르면(=자동 수정이 반영됨) 중단하고,
                   기존 원본은 _build/<program>_original_prev.py 로 한 번 보존한다(일반 지침 7).

검증 내용
1) 정답 소스(_build/<program>_ref.py)로 채점 식의 기대값을 계산한다.
2) 오류 100개(번호 1~100, 분야 10종 x 10)를 하나씩만 넣어 각각 최소 1개 식에서 실패하는지 확인한다.
3) 100개를 모두 넣은 결함 소스를 만든다. 각 '정답 코드' 조각은 넣는 시점에 정확히 1번만 나와야 한다(겹침 금지).
4) 오류별 채점 식: 그 오류만 잡는 '전용 식'이 있으면 그것, 없으면 그 오류를 잡는 식 전체(공유)로 기록한다.
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
AIS = ("gemini", "openai", "claude", "ollama")


def _load(source):
    """소스 문자열을 새 모듈로 실행한다. 실패하면 예외 객체를 돌려준다."""
    module = types.ModuleType("target")
    try:
        exec(compile(source, "target", "exec"), module.__dict__)  # noqa: S102 - 생성기 내부 소스만 실행
    except Exception as exc:  # noqa: BLE001
        return exc
    return module


def _failing(module, case_list, want):
    """기대값과 다른 식 번호 목록(모듈 로드 실패면 전부)."""
    if isinstance(module, Exception):
        return list(range(len(case_list)))
    return [i for i, expr in enumerate(case_list) if not bs.matches(bs.run_case(module, expr), want[i])]


def build(program, write_targets, rewrite=False):
    ref = (BUILD_DIR / f"{program}_ref.py").read_text(encoding="utf-8")
    case_list = bs.cases(program)
    mutations = importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard._build.{program}_mutations").M
    ref_module = _load(ref)
    want = [bs.run_case(ref_module, expr) for expr in case_list]
    if sorted(m[0] for m in mutations) != list(range(1, 101)):
        raise SystemExit(f"{program}: 오류 번호는 1..100 이어야 함")
    detect = {}
    for no, _cat, func, desc, pairs in mutations:
        source = ref
        for old, new in pairs:
            if ref.count(old) != 1:
                raise SystemExit(f"{program} #{no}: 정답 코드가 1번이 아님: {old!r}")
            source = source.replace(old, new)
        fails = _failing(_load(source), case_list, want)
        if not fails:
            raise SystemExit(f"{program} #{no} {func}: 이 오류를 잡는 식이 없음 ({desc})")
        detect[no] = fails
    buggy = ref
    for no, _cat, _func, _desc, pairs in mutations:
        for old, new in pairs:
            if buggy.count(old) != 1:
                raise SystemExit(f"{program} #{no}: 합칠 때 다른 오류와 겹침: {old!r}")
            buggy = buggy.replace(old, new)
    compile(buggy, program, "exec")
    buggy_fails = set(_failing(_load(buggy), case_list, want))
    owners = {}
    for no, fails in detect.items():
        for i in fails:
            owners.setdefault(i, set()).add(no)
    bugmap, masked = [], []
    for no, cat, func, desc, _pairs in mutations:
        # 100개를 모두 넣은 파일에서도 실제로 실패하는 식만 쓴다(다른 오류에 가려진 식은 판정 근거가 못 됨).
        visible = [i for i in detect[no] if i in buggy_fails]
        exclusive = [i for i in visible if owners[i] == {no}]
        if not visible:
            masked.append(f"#{no} {func}")
        bugmap.append({"no": no, "category": cat, "function": func, "description": desc,
                       "cases": exclusive or visible, "exclusive": bool(exclusive)})
    if masked:
        raise SystemExit(f"{program}: 다른 오류에 가려 전체 파일에서 드러나지 않는 오류: {masked}")
    (BUILD_DIR / f"{program}_expected.json").write_text(json.dumps(
        [[kind, value if kind == "raises" else repr(value)] for kind, value in want], ensure_ascii=False),
        encoding="utf-8")
    (BUILD_DIR / f"{program}_bugmap.json").write_text(json.dumps(bugmap, ensure_ascii=False, indent=1),
                                                      encoding="utf-8")
    written = []
    if write_targets or rewrite:
        targets = [HARD_DIR / f"{program}_original.py"] + [HARD_DIR / f"{program}_{ai}.py" for ai in AIS]
        existing = [str(path.name) for path in targets if path.exists()]
        if rewrite:
            previous = targets[0].read_bytes() if targets[0].exists() else None
            # AI가 고쳐 둔 사본(기존 원본과 내용이 다름)은 결과 보존을 위해 절대 덮어쓰지 않는다.
            changed = [path.name for path in targets[1:] if path.exists() and path.read_bytes() != previous]
            if changed:
                raise SystemExit(f"{program}: 자동 수정이 반영된 사본이 있어 다시 쓰지 않음: {changed}")
            backup = BUILD_DIR / f"{program}_original_prev.py"
            if previous is not None and not backup.exists():
                backup.write_bytes(previous)
        elif existing:
            raise SystemExit(f"{program}: 이미 있는 대상 파일은 덮어쓰지 않음: {existing}")
        for path in targets:
            path.write_text(buggy, encoding="utf-8")
            written.append(path.name)
    categories = {}
    for m in mutations:
        categories[m[1]] = categories.get(m[1], 0) + 1
    return {"program": program, "cases": len(case_list), "bugs": len(mutations), "categories": categories,
            "exclusive_bugs": sum(b["exclusive"] for b in bugmap),
            "buggy_failing_cases": len(buggy_fails),
            "buggy_chars": len(buggy), "written": written}


def main():
    write_targets = "--write-targets" in sys.argv
    rewrite = {arg.split("=", 1)[1] for arg in sys.argv[1:] if arg.startswith("--rewrite=")}
    unknown = rewrite - set(bs.PROGRAMS)
    if unknown:  # 잘못된 입력: 없는 프로그램 이름
        raise SystemExit(f"알 수 없는 프로그램: {sorted(unknown)} (허용: {list(bs.PROGRAMS)})")
    print(json.dumps([build(program, write_targets, program in rewrite) for program in bs.PROGRAMS],
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
