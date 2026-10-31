import pytest


def _payload():
    return {
        "mode": "source_analysis",
        "keyword": "target",
        "read_targets": [{"path": "haness/mcp/tools/orchestrator_tools.py", "start_line": 1, "max_lines": 10}],
        "change_set": {"mode": "change_set"},
    }


def test_source_analysis_orders_search_read_change_and_diff(monkeypatch):
    from haness.mcp.tools import source_analysis_graph as module

    calls = []

    def search(**kwargs):
        calls.append("source_search")
        return [{"path": "haness/mcp/tools/orchestrator_tools.py", "line_no": 1}]

    def read(**kwargs):
        calls.append("source_read")
        return {"path": kwargs["path"], "content": []}

    def change(payload, dry_run):
        calls.append(("change_set", dry_run))
        return {"success": True, "state": "PLANNED"}

    def diff(**kwargs):
        calls.append("git_diff")
        return {"diff": []}

    monkeypatch.setattr(module, "source_search", search)
    monkeypatch.setattr(module, "source_read", read)
    monkeypatch.setattr(module, "run_change_set", change)
    monkeypatch.setattr(module, "git_diff", diff)

    result = module.run_source_analysis(_payload(), dry_run=True)

    assert calls == ["source_search", "source_read", ("change_set", True), "git_diff"]
    assert result["success"] is True
    assert result["state"] == "VERIFIED"


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "source_analysis", "keyword": "", "read_targets": [], "change_set": {}},
        {"mode": "source_analysis", "keyword": "x", "read_targets": [], "change_set": {}},
        {"mode": "source_analysis", "keyword": "x", "read_targets": [{"path": "x"}]},
    ],
)
def test_source_analysis_rejects_invalid_input(payload):
    from haness.mcp.tools.source_analysis_graph import run_source_analysis

    with pytest.raises(ValueError):
        run_source_analysis(payload, dry_run=True)
