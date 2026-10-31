"""(1회성) 수집기·자기수리 테스트를 haness/tests로 옮기고, 변경 실행기 테스트 경로 규칙을 haness/tests로 바꾼다.

근거: 2026-10-25 LuckyBoys 일반 지침 10 보충
      "test, output, report, temp 등 소스는 haness 폴더로" / 변경 실행기는 "haness/tests만 허용".
입력(stdin JSON): {"dry_run": true}
  - dry_run=true : 바꿀 파일·치환 위치·이동 계획만 출력(아무것도 바꾸지 않음)
  - dry_run=false: git mv로 이동(이력 보존) → 정확히 1회 나오는 문자열만 치환
원본 보존: 실행 전 backup_files_before_edit.py로 백업한다(이 스크립트는 백업하지 않음).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 이번 수집기 작업에서 만든 테스트(다른 세션 테스트는 옮기지 않음)
MOVES = [
    "test_public_document_catalog_collector.py",
    "test_collector_seedless_post_download.py",
    "test_collector_self_heal.py",
    "test_collector_worker_self_heal.py",
    "test_profile_autodiscover_inference.py",
    "test_autodiscover_failure_classification.py",
    "test_autodiscover_self_repair.py",
]
# 옮긴 테스트는 한 단계 깊어지므로 프로젝트 루트 계산을 parents[1] → parents[2]로 바꾼다.
ROOT_OLD = "ROOT = Path(__file__).resolve().parents[1]"
ROOT_NEW = "ROOT = Path(__file__).resolve().parents[2]"

# (파일, old, new): 변경 실행기 테스트 경로 규칙
EDITS = [
    ("haness/mcp/tools/change_set_graph.py",
     '    if any(not path.startswith("tests/") for path in test_paths):\n'
     '        raise ValueError("test_paths must stay under tests/")',
     '    # 2026-10-25 LuckyBoys: 테스트는 haness/tests 아래만 허용(일반 지침 10 — test 소스는 haness로).\n'
     '    if any(not path.startswith("haness/tests/") for path in test_paths):\n'
     '        raise ValueError("test_paths must stay under haness/tests/")'),
    ("tests/harness/mcp/test_sps_change_set_tool.py",
     '"test_paths": ["tests/test_example.py"],', '"test_paths": ["haness/tests/test_example.py"],'),
    ("tests/harness/mcp/test_source_partner_agent.py",
     '"test_paths": ["tests/harness/mcp/test_source_partner_agent.py"],',
     '"test_paths": ["haness/tests/test_source_partner_agent.py"],'),
    ("haness/mcp/agents/source_partner_agent.py",
     '  "test_paths": ["tests/..."],', '  "test_paths": ["haness/tests/..."],'),
    ("haness/mcp/agents/source_partner_agent.py",
     '"writes": [{"path": "haness/... 또는 tests/...",', '"writes": [{"path": "haness/... 또는 haness/tests/...",'),
    ("haness/mcp/agents/source_partner_agent.py",
     '"stage_groups": {"source": ["..."], "tests": ["..."],', '"stage_groups": {"source": ["..."], "tests": ["haness/tests/..."],'),
]


def main() -> None:
    dry_run = json.loads(sys.stdin.read() or "{}").get("dry_run", True)
    plan, errors = {"moves": [], "edits": []}, []
    for name in MOVES:
        source, target = ROOT / "tests" / name, ROOT / "haness/tests" / name
        text = source.read_text(encoding="utf-8") if source.is_file() else ""
        item = {"from": f"tests/{name}", "to": f"haness/tests/{name}", "exists": source.is_file(),
                "target_free": not target.exists(), "root_line_count": text.count(ROOT_OLD)}
        if not (item["exists"] and item["target_free"] and item["root_line_count"] == 1):
            errors.append(item)
        plan["moves"].append(item)
    for path, old, new in EDITS:
        text = (ROOT / path).read_text(encoding="utf-8")
        item = {"path": path, "count": text.count(old)}
        if item["count"] != 1:
            errors.append(item)
        plan["edits"].append(item)
    plan["errors"] = errors
    if dry_run or errors:
        plan["applied"] = False
        print(json.dumps(plan, ensure_ascii=False, indent=1))
        return
    for name in MOVES:
        subprocess.run(["git", "mv", f"tests/{name}", f"haness/tests/{name}"], cwd=ROOT, check=True,
                       capture_output=True, text=True)
        target = ROOT / "haness/tests" / name
        target.write_text(target.read_text(encoding="utf-8").replace(ROOT_OLD, ROOT_NEW, 1), encoding="utf-8")
    for path, old, new in EDITS:
        file = ROOT / path
        file.write_text(file.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    plan["applied"] = True
    print(json.dumps(plan, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
