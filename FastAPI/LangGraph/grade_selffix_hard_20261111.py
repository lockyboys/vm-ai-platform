"""어려운 자가 수정 시험(프로그램별 오류 100개) AI 4종 채점 보고서 (2026-11-11, LuckyBoys 요청).

무엇을 하나
- review_python_source job 결과(result.json)에서 hard/<program>_<ai>.py 를 대상으로 한 최신 job을 찾는다.
- 두 가지를 채점한다.
  ① 수정안(job 폴더 proposed.py): AI가 무엇을 고쳤는지
  ② 현재 파일(자동 적용 후 남은 소스): 실제로 소스가 바뀌었는지(테스트 전부 통과해야만 남는다)
- 오류별 판정: 그 오류를 잡는 채점 식이 모두 통과하면 '고침'. 전용 식이 없는 오류는 공유 식으로 판정(표에 * 표시).
- 결과를 harness/memory/selffix_bench/report_hard_20261111.md 로 저장하고 요약 JSON을 출력한다.

안전: LLM 호출 없음. 소스·job 폴더는 읽기만 한다(보고서만 쓴다).
"""
import json
import sys
import types
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
sys.path.insert(0, str(ROOT))
from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs  # noqa: E402

HARD_DIR = ROOT / "FastAPI/LangGraph/selffix_demo/hard"
REVIEW_DIR = ROOT / "harness/memory/source_reviews"
REPORT_PATH = ROOT / "harness/memory/selffix_bench/report_hard_20261111.md"
AIS = ("gemini", "openai", "claude", "ollama")
LABELS = {"original": "원본(오류 100개)", "gemini": "Gemini", "openai": "ChatGPT", "claude": "Claude", "ollama": "Ollama"}


def _load(source):
    """소스 문자열을 새 모듈로 실행(파일별로 독립된 모듈). 실패하면 예외 객체."""
    module = types.ModuleType("target")
    try:
        exec(compile(source, "target", "exec"), module.__dict__)  # noqa: S102 - 채점 대상 소스 실행이 목적
    except Exception as exc:  # noqa: BLE001
        return exc
    return module


def _grade(source, program):
    """소스 하나를 채점: 통과 식 수, 오류별 고침 여부."""
    case_list, want, bugs = bs.cases(program), bs.expected(program), bs.bugmap(program)
    module = _load(source)
    if isinstance(module, Exception):
        passed = [False] * len(case_list)
    else:
        passed = [bs.matches(bs.run_case(module, expr), want[i]) for i, expr in enumerate(case_list)]
    fixed = {b["no"]: all(passed[i] for i in b["cases"]) for b in bugs}
    return {"cases_passed": sum(passed), "cases_total": len(case_list), "bugs_fixed": sum(fixed.values()),
            "fixed": fixed, "load_error": type(module).__name__ if isinstance(module, Exception) else None}


def _latest_jobs():
    """대상 파일별 가장 최근 job의 result.json."""
    latest = {}
    for result_path in REVIEW_DIR.glob("job_*/result.json"):
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        source = str(result.get("source_path", ""))
        if "selffix_demo/hard/" not in source:
            continue
        key = Path(source).stem
        if key not in latest or result.get("started_at", 0) > latest[key][1].get("started_at", 0):
            latest[key] = (result_path.parent, result)
    return latest


def main():
    jobs = _latest_jobs()
    summary, lines = {}, []
    for program in bs.PROGRAMS:
        bugs = bs.bugmap(program)
        rows = {"original": {"file": _grade((HARD_DIR / f"{program}_original.py").read_text(encoding="utf-8"), program)}}
        for ai in AIS:
            job_dir, result = jobs.get(f"{program}_{ai}", (None, {}))
            # 2026-11-11 수정: 피드백 재시도가 있으면 마지막 라운드 수정안(final_proposed_path)으로 채점한다.
            # (이전에는 1차 수정안만 채점해 '2차에서 다 고친' 결과가 98/100처럼 낮게 보였다.)
            final = result.get("final_proposed_path")
            proposed = (ROOT / final) if final else (job_dir / "proposed.py" if job_dir else None)
            apply = result.get("auto_apply_result") or {}
            rows[ai] = {
                "job": job_dir.name if job_dir else None, "state": result.get("state"),
                "seconds": result.get("elapsed_seconds"), "verified": result.get("model_verified"),
                "reasons": result.get("verification_reasons"), "applied": apply.get("applied"),
                "rolled_back": apply.get("rolled_back"), "apply_reason": apply.get("reason"),
                "proposal": _grade(proposed.read_text(encoding="utf-8"), program) if proposed and proposed.is_file() else None,
                "file": _grade((HARD_DIR / f"{program}_{ai}.py").read_text(encoding="utf-8"), program),
            }
        summary[program] = rows
        n_cases = rows["original"]["file"]["cases_total"]
        lines += [f"## {program} (오류 100개, 채점 식 {n_cases}개)", "",
                  "| AI | 상태 | 시간(초) | 검증 통과 | 수정안: 고친 오류 | 수정안: 통과 식 | 자동 적용 | 현재 파일: 남은 오류 |",
                  "|---|---|---|---|---|---|---|---|"]
        base = rows["original"]["file"]
        lines.append(f"| {LABELS['original']} | - | - | - | 0/100 | {base['cases_passed']}/{n_cases} | - | {100 - base['bugs_fixed']} |")
        for ai in AIS:
            r = rows[ai]
            prop = r["proposal"]
            applied = "적용" if r["applied"] else ("되돌림" if r["rolled_back"] else f"안 함({r['apply_reason'] or '제안 없음'})")
            lines.append(f"| {LABELS[ai]} | {r['state']} | {r['seconds']} | {r['verified']} | "
                         f"{prop['bugs_fixed'] if prop else '-'}/100 | {prop['cases_passed'] if prop else '-'}/{n_cases} | "
                         f"{applied} | {100 - r['file']['bugs_fixed']} |")
        lines += ["", "### 분야별 고친 오류 수(수정안 기준, 분야당 10개)", "",
                  "| 분야 | " + " | ".join(LABELS[a] for a in AIS) + " |", "|---|" + "---|" * len(AIS)]
        for cat in dict.fromkeys(b["category"] for b in bugs):
            nos = [b["no"] for b in bugs if b["category"] == cat]
            cells = []
            for ai in AIS:
                prop = rows[ai]["proposal"]
                cells.append(str(sum(prop["fixed"][n] for n in nos)) if prop else "-")
            lines.append(f"| {cat} | " + " | ".join(cells) + " |")
        lines += ["", "### 오류별 결과(수정안 기준, O=고침 X=못 고침 -=수정안 없음, *=공유 채점 식)", "",
                  "| # | 분야 | 함수 | 심은 오류 | " + " | ".join(LABELS[a] for a in AIS) + " |",
                  "|---|---|---|---|" + "---|" * len(AIS)]
        for b in bugs:
            marks = []
            for ai in AIS:
                prop = rows[ai]["proposal"]
                marks.append(("O" if prop["fixed"][b["no"]] else "X") if prop else "-")
            star = "" if b["exclusive"] else "*"
            lines.append(f"| {b['no']}{star} | {b['category']} | `{b['function']}` | {b['description']} | " + " | ".join(marks) + " |")
        lines.append("")
    head = ["# 어려운 자가 수정 시험 — 오류 100개 x 2 프로그램, AI 4종 (2026-11-11)", "",
            "- 대상: FastAPI/LangGraph/selffix_demo/hard/<program>_<ai>.py (AI마다 같은 결함 사본, 원본은 *_original.py로 보존)",
            "- 자동 적용: 채점 식을 전부 통과해야 적용되고, 하나라도 실패하면 원래 소스로 되돌린다.",
            "- 오류는 분야 10종 x 10개로 고르게 심었다(분야별 표 참고).", ""]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(head + lines) + "\n", encoding="utf-8")
    compact = {p: {ai: {k: v for k, v in r.items() if k not in ("proposal", "file", "reasons")} |
                   {"proposal_fixed": r["proposal"]["bugs_fixed"] if r.get("proposal") else None,
                    "file_bugs_left": 100 - r["file"]["bugs_fixed"]}
                   for ai, r in rows.items()} for p, rows in summary.items()}
    print(json.dumps({"report": str(REPORT_PATH.relative_to(ROOT)), "summary": compact}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
