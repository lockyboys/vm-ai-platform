"""AI 4종 자가 수정 결과를 테스트 100건 x 2개 프로그램으로 건별 채점 (2026-11-10, LuckyBoys 요청).

무엇을 하나
- 이미 끝난 review_python_source job의 제안 소스(proposed.py, 없으면 recheck_proposed.py)를
  임시 폴더에 원래 모듈 이름으로 복사하고, 같은 100건 테스트(bench_*_100.py)를 돌린다.
- "원본"(일부러 결함을 넣은 소스)도 같이 돌려 기준선으로 보여 준다.
- 결과: 건별 통과/실패 표 + AI별 요약 + 원본 대비 수정 내용(diff)을 Markdown 보고서로 저장한다.

안전
- LLM 호출 없음(비용 0). 원본 소스·job 폴더는 읽기만 하고, 보고서만 새로 쓴다.
- pytest는 임시 폴더에서 실행하고 PYTHONPATH를 그 폴더로만 둬 저장소 원본이 import되지 않게 한다.
"""
import difflib
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
DEMO_DIR = ROOT / "FastAPI/LangGraph/selffix_demo"
BENCH_DIR = DEMO_DIR / "bench"
REVIEW_DIR = ROOT / "harness/memory/source_reviews"
REPORT_DIR = ROOT / "harness/memory/selffix_bench"
REPORT_PATH = REPORT_DIR / "report_100_20261110.md"

# 프로그램별 (모듈 파일, 100건 테스트 파일)
PROGRAMS = {
    "calculator": ("calculator.py", "bench_calculator_100.py"),
    "tetris": ("tetris_core.py", "bench_tetris_100.py"),
}
# AI별 job id (compare_selffix_providers_20261110.py와 같은 최종 job)
JOBS = {
    "calculator": {"gemini": "a750b05948694dc9b18347a15ead0a02", "openai": "cb3e3d7278a0469a89273adb96d02411",
                   "claude": "24a9715c95fb46b5b039240a82a9043f", "ollama": "b3bcbc53742c4c1db279c7b72d6a3208"},
    "tetris": {"gemini": "db2687fba5634ac798c883ca41147265", "openai": "b1019760bff04491bcde797d29df9b34",
               "claude": "2b1d6d67407d4cafbd3e515b9ce5c9c5", "ollama": "130c8cf0776c4b4389836eea09fc4bc8"},
}
LABELS = {"original": "원본(결함)", "gemini": "Gemini", "openai": "ChatGPT", "claude": "Claude", "ollama": "Ollama"}


def _proposal(job_id: str):
    """job 폴더에서 채점할 제안 소스를 찾는다. Claude 1차 판정 오탐 건은 recheck_proposed.py를 쓴다."""
    job_dir = REVIEW_DIR / ("job_" + job_id)
    for name in ("proposed.py", "recheck_proposed.py"):
        if (job_dir / name).is_file():
            return job_dir / name
    return None


def _run_bench(source: Path, module_file: str, bench_file: str) -> dict:
    """임시 폴더에서 bench를 돌려 {테스트 id: 'pass'|'fail'|'error'}를 돌려준다."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "FastAPI/LangGraph/selffix_demo"
        pkg.mkdir(parents=True)
        shutil.copy(source, pkg / module_file)
        shutil.copy(BENCH_DIR / bench_file, Path(tmp) / bench_file)
        xml_path = Path(tmp) / "result.xml"
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        f"--junitxml={xml_path}", bench_file],
                       cwd=tmp, capture_output=True, text=True, timeout=300,
                       env={"PYTHONPATH": tmp, "PATH": "/usr/bin:/bin"})
        outcomes = {}
        if not xml_path.is_file():  # 수집 단계에서 import 실패 등
            return outcomes
        for case in ET.parse(xml_path).getroot().iter("testcase"):
            status = "pass"
            if case.find("failure") is not None:
                status = "fail"
            elif case.find("error") is not None:
                status = "error"
            outcomes[case.get("name")] = status
        return outcomes


def _diff(original: Path, proposal: Path) -> str:
    """원본 대비 제안 소스의 unified diff(주석·공백 포함 전체)."""
    lines = difflib.unified_diff(original.read_text(encoding="utf-8").splitlines(),
                                 proposal.read_text(encoding="utf-8").splitlines(),
                                 "원본", "제안", lineterm="")
    return "\n".join(lines) or "(변경 없음)"


def main() -> None:
    summary, sections = {}, []
    for program, (module_file, bench_file) in PROGRAMS.items():
        original = DEMO_DIR / module_file
        sources = {"original": original}
        for ai, job_id in JOBS[program].items():
            sources[ai] = _proposal(job_id)
        results = {ai: (_run_bench(src, module_file, bench_file) if src else {}) for ai, src in sources.items()}
        test_ids = list(results["original"]) or sorted({t for r in results.values() for t in r})
        summary[program] = {ai: {"passed": sum(v == "pass" for v in r.values()), "total": len(test_ids)}
                            for ai, r in results.items()}
        cols = list(sources)
        out = [f"## {program} (테스트 {len(test_ids)}건)", "",
               "| AI | 통과 | 실패 | 제안 소스 |", "|---|---|---|---|"]
        for ai in cols:
            src = sources[ai]
            passed = summary[program][ai]["passed"]
            out.append(f"| {LABELS[ai]} | {passed} | {len(test_ids) - passed} | "
                       f"{src.relative_to(ROOT) if src else '없음'} |")
        out += ["", "### 건별 결과 (O=통과, X=실패, E=오류, -=미실행)", "",
                "| # | 테스트 | " + " | ".join(LABELS[c] for c in cols) + " |",
                "|---|---|" + "---|" * len(cols)]
        mark = {"pass": "O", "fail": "X", "error": "E"}
        for i, tid in enumerate(test_ids, 1):
            out.append(f"| {i} | `{tid}` | " + " | ".join(mark.get(results[c].get(tid), "-") for c in cols) + " |")
        out += ["", "### AI별 수정 내용 (원본 대비 diff)", ""]
        for ai in cols[1:]:
            src = sources[ai]
            out += [f"#### {LABELS[ai]}", "", "```diff", _diff(original, src) if src else "(제안 없음)", "```", ""]
        sections.append("\n".join(out))
    head = ["# 자가 수정 AI 4종 비교 — 테스트 100건 x 2 (2026-11-10)", "",
            "- 채점: 같은 100건 테스트를 원본(결함)과 각 AI 제안 소스에 돌림. LLM 재호출 없음.",
            "- Claude는 1차 판정 때 출력 계약 오탐으로 proposed.py가 없어 review.md에서 다시 뽑은 recheck_proposed.py로 채점.",
            "", "| 프로그램 | " + " | ".join(LABELS.values()) + " |", "|---|" + "---|" * len(LABELS)]
    for program, row in summary.items():
        head.append(f"| {program} | " + " | ".join(f"{row[a]['passed']}/{row[a]['total']}" for a in LABELS) + " |")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(head) + "\n\n" + "\n\n".join(sections) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH.relative_to(ROOT)), "summary": summary}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
