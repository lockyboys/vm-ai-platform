"""haness/source_repair.py가 LangGraph StateGraph(add_node/add_edge/compile)로 실행되는지 검증한다.

2026-10-25 LuckyBoys: "source_repair.py 자체도 LangGraph로 바꿔 주세요" → repair_source의 단계
(재현 확인 → 후보 검증 → 적용(백업·쓰기·재검증·실패 시 원복) → git add)를 노드·엣지로 바꾼다.
공개 함수 repair_source(...)의 인자·반환·예외는 그대로 유지한다(Sniffer·PARTNER 도구가 그대로 호출).

검증 항목 (임시 git 저장소, 네트워크·LLM 없음)
1. build_repair_graph()가 CompiledStateGraph이고 노드 baseline·candidate·apply·stage를 가진다
2. repair_source가 그 그래프를 실제로 거친다(빌더 감시)
3. 후보가 테스트를 통과 못 하면 apply/stage 노드로 가지 않는다(파일·stage 그대로, success False)
4. 잘못된 입력: 원본에서 이미 통과하는 테스트(재현 안 됨)는 그래프 안에서 ValueError로 거부
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NODES = {"baseline", "candidate", "apply", "stage"}
TEST = '''import importlib.util, unittest
spec = importlib.util.spec_from_file_location("calc", SOURCE_PATH)
calc = importlib.util.module_from_spec(spec); spec.loader.exec_module(calc)
class T(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)
'''


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """임시 git 저장소 + 허용 목록에 올린 대상 파일 1개(커밋된 상태)."""
    spec = importlib.util.spec_from_file_location("source_repair_graph_t", ROOT / "haness/source_repair.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    git = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    target = tmp_path / "pkg/calc.py"
    target.parent.mkdir()
    target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "init")
    monkeypatch.setattr(module, "_root", lambda: tmp_path)
    monkeypatch.setattr(module.config, "SPS_SOURCE_REPAIR_ALLOWED_PATHS", ("pkg/calc.py",))
    monkeypatch.setattr(module.config, "SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(module.config, "SPS_SOURCE_REPAIR_AUDIT_DIR", "audit")
    return module, tmp_path, git


def test_build_repair_graph_is_compiled_state_graph(repo):
    from langgraph.graph.state import CompiledStateGraph

    module, _, _ = repo
    graph = module.build_repair_graph()
    assert isinstance(graph, CompiledStateGraph)
    assert NODES <= set(graph.get_graph().nodes)


def test_repair_source_runs_through_graph(repo, monkeypatch):
    module, _, _ = repo
    built = []
    original = module.build_repair_graph
    monkeypatch.setattr(module, "build_repair_graph", lambda: built.append(1) or original())
    sha = module.read_repair_source("pkg/calc.py")["sha256"]
    report = module.repair_source("pkg/calc.py", "return a - b", "return a + b", TEST, sha, dry_run=True)
    assert built == [1] and report["success"] is True and report["applied"] is False


def test_failed_candidate_does_not_reach_apply_or_stage(repo):
    module, root, git = repo
    sha = module.read_repair_source("pkg/calc.py")["sha256"]
    report = module.repair_source("pkg/calc.py", "return a - b", "return 3", TEST, sha, dry_run=False)
    assert report["success"] is False and report["applied"] is False
    assert "a - b" in (root / "pkg/calc.py").read_text(encoding="utf-8")
    assert git("diff", "--cached", "--name-only").stdout.decode().strip() == ""


def test_test_that_already_passes_is_rejected(repo):
    module, _, _ = repo
    sha = module.read_repair_source("pkg/calc.py")["sha256"]
    passing = TEST.replace("calc.add(2, 3), 5", "calc.add(3, 3), 0")   # 원본(a-b)에서 이미 통과 → 재현 아님
    with pytest.raises(ValueError):
        module.repair_source("pkg/calc.py", "return a - b", "return a + b", passing, sha, dry_run=True)
