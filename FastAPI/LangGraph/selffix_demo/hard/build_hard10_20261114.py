"""아주 어려운 오류 10개 시험 세트 생성기 (2026-11-14, LuckyBoys 요청: "아주 어렵게 각각 10건만").

무엇을 만드나
- 프로그램(계산기 calc_engine, 테트리스 tetris_engine)마다 오류 10개짜리 결함 소스를 만든다.
- 기존 오류 100개(_build/<program>_mutations.py, 분야 10종 x 10) 중에서 분야마다 1개씩 고른다.
  '어려운 것' 기준: 그 오류 하나만 넣었을 때 실패하는 채점 식 수가 가장 적은 것
  (= 드러나는 곳이 적어 찾기 어렵다). 같으면 번호가 작은 것.
- 채점 식·기대값은 기존 것(_build/<program>_cases_src.py, 정답 구현 _build/<program>_ref.py)을 그대로 쓴다.

실행
  python FastAPI/LangGraph/selffix_demo/hard/build_hard10_20261114.py          # dry-run: 고를 오류만 출력
  python FastAPI/LangGraph/selffix_demo/hard/build_hard10_20261114.py --write  # 파일 생성
생성 파일(이미 있으면 덮어쓰지 않고 중단 — 자동 수정 결과 보존, 일반 지침 7)
  hard10/<program>_original.py   보존용 결함 원본
  hard10/<program>_gemini.py     Gemini가 스스로 고칠 대상
  hard10/<program>_bugmap.json   고른 오류 10개 목록(번호·분야·함수·설명·드러나는 식 수)
검증: 10개를 모두 넣은 파일에서도 오류마다 실패 식이 최소 1개 있어야 한다(가려진 오류 금지).
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
OUT_DIR = HARD_DIR / "hard10"
AIS = ("gemini",)          # 이번 요청은 Gemini만. 다른 AI가 필요하면 여기에 이름을 더한다.
BUGS_PER_CATEGORY = 1      # 분야 10종 x 1 = 10개


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


def _apply(source, pairs):
    """정답 코드 조각을 결함 코드로 바꾼다. 조각은 정확히 1번만 나와야 한다(겹침 금지)."""
    for old, new in pairs:
        if source.count(old) != 1:
            raise SystemExit(f"정답 코드 조각이 1번이 아님: {old!r}")
        source = source.replace(old, new)
    return source


def build(program, write):
    ref = (BUILD_DIR / f"{program}_ref.py").read_text(encoding="utf-8")
    case_list = bs.cases(program)
    want = [bs.run_case(_load(ref), expr) for expr in case_list]
    mutations = importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard._build.{program}_mutations").M
    # 1) 오류 하나씩 넣어 실패 식 수를 센다(적을수록 어렵다).
    scored = []
    for no, cat, func, desc, pairs in mutations:
        fails = _failing(_load(_apply(ref, pairs)), case_list, want)
        scored.append((len(fails), no, cat, func, desc, pairs))
    # 2) 분야마다 가장 어려운 것 1개.
    chosen, seen = [], {}
    for item in sorted(scored, key=lambda x: (x[0], x[1])):
        if seen.get(item[2], 0) < BUGS_PER_CATEGORY:
            seen[item[2]] = seen.get(item[2], 0) + 1
            chosen.append(item)
    chosen.sort(key=lambda x: x[1])
    # 3) 10개를 모두 넣은 결함 소스 + 가려진 오류 검사.
    buggy = ref
    for item in chosen:
        buggy = _apply(buggy, item[5])
    compile(buggy, program, "exec")
    buggy_fails = set(_failing(_load(buggy), case_list, want))
    bugmap, masked = [], []
    for n_fail, no, cat, func, desc, pairs in chosen:
        single = set(_failing(_load(_apply(ref, pairs)), case_list, want))
        visible = sorted(single & buggy_fails)
        if not visible:
            masked.append(f"#{no} {func}")
        bugmap.append({"no": no, "category": cat, "function": func, "description": desc,
                       "single_fail_cases": n_fail, "cases": visible})
    if masked:
        raise SystemExit(f"{program}: 다른 오류에 가려 드러나지 않는 오류: {masked}")
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
    return {"program": program, "cases": len(case_list), "bugs": len(chosen),
            "buggy_failing_cases": len(buggy_fails),
            "chosen": [{k: b[k] for k in ("no", "category", "function", "single_fail_cases")} for b in bugmap],
            "written": written}


def main():
    unknown = [a for a in sys.argv[1:] if a != "--write"]
    if unknown:  # 잘못된 입력: 모르는 인자
        raise SystemExit(f"알 수 없는 인자: {unknown} (허용: --write)")
    print(json.dumps([build(p, "--write" in sys.argv) for p in bs.PROGRAMS], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
