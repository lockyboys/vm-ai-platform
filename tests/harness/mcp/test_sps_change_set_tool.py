"""LangChain 도구와 LangGraph 기반 SPS 변경 세트 실행을 검증한다."""

import asyncio
import json

import pytest

from haness.mcp.tools import change_set_graph as module
from haness.mcp.tools import orchestrator_tools


def _work_order(*, confirmed=False):
    """테스트에서 공통으로 사용하는 유효한 소스 변경 세트를 반환한다."""
    return {
        "mode": "change_set",
        "change_set_id": "change-001",
        "apply_confirmed": confirmed,
        "patch_text": (
            "--- a/haness/example.py\n"
            "+++ b/haness/example.py\n"
            "@@ -1 +1 @@\n"
            "-OLD = True\n"
            "+OLD = False\n"
        ),
        "test_paths": ["tests/test_example.py"],
        "stage_groups": {
            "source": ["haness/example.py"],
            "tests": [],
            "docs": [],
            "operations": [],
        },
        "activation": {
            "required": False,
            "target": "",
            "method": "none",
            "verification": "pytest",
        },
    }


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value.pop("change_set_id"),
        lambda value: value.update(change_set_id="../bad"),
        lambda value: value.update(test_paths=[]),
        lambda value: value["stage_groups"].update(source=[]),
        lambda value: value["stage_groups"].update(tests=["haness/example.py"]),
    ],
)
def test_invalid_change_set_is_rejected_before_mutation(monkeypatch, mutator):
    """잘못된 입력은 patch·테스트·Git 변경 전에 거부해야 한다."""
    work_order = _work_order()
    mutator(work_order)
    patch_calls = []
    monkeypatch.setattr(
        module,
        "source_patch",
        lambda *args, **kwargs: patch_calls.append((args, kwargs)),
    )

    with pytest.raises(ValueError):
        module.run_change_set(work_order, dry_run=True)

    assert patch_calls == []


def test_change_set_dry_run_checks_patch_and_stage_without_mutation(monkeypatch):
    """dry-run은 patch와 정확한 Git 경로만 검사하고 적용하지 않아야 한다."""
    patch_calls = []
    stage_calls = []
    monkeypatch.setattr(
        module,
        "source_patch",
        lambda patch_text, dry_run=True: patch_calls.append(dry_run)
        or {
            "dry_run": dry_run,
            "applicable": True,
            "paths": ["haness/example.py"],
            "before_sha256": {"haness/example.py": "before"},
            "patch_sha256": "patch",
        },
    )
    monkeypatch.setattr(
        module,
        "git_add",
        lambda paths, dry_run=True: stage_calls.append((list(paths), dry_run))
        or {"dry_run": dry_run, "requested_paths": list(paths), "staged_paths": []},
    )

    result = module.run_change_set(_work_order(), dry_run=True)

    assert result["state"] == "PLANNED"
    assert patch_calls == [True]
    assert stage_calls == [(["haness/example.py"], True)]
    assert "evidence_path" not in result


def test_patch_paths_must_match_stage_groups(monkeypatch):
    """모델이 낸 patch 경로와 분리 저장 경로가 다르면 실행을 중단해야 한다."""
    monkeypatch.setattr(
        module,
        "source_patch",
        lambda patch_text, dry_run=True: {
            "dry_run": True,
            "applicable": True,
            "paths": ["haness/other.py"],
        },
    )

    with pytest.raises(ValueError, match="change paths and stage_groups differ"):
        module.run_change_set(_work_order(), dry_run=True)


def test_apply_runs_patch_tests_and_separate_git_add(monkeypatch):
    """승인 실행은 patch, pytest, 정확한 source 그룹 저장 순서를 지켜야 한다."""
    patch_calls = []
    stage_calls = []
    monkeypatch.setattr(module, "_staged_paths", lambda: [])
    monkeypatch.setattr(
        module,
        "source_patch",
        lambda patch_text, dry_run=True: patch_calls.append(dry_run)
        or {
            "dry_run": dry_run,
            "applicable": True,
            "applied": not dry_run,
            "paths": ["haness/example.py"],
            "before_sha256": {"haness/example.py": "before"},
            "after_sha256": {"haness/example.py": "after"},
            "patch_sha256": "patch",
        },
    )
    monkeypatch.setattr(
        module,
        "run_pytest_verification",
        lambda paths, title="": {
            "success": True,
            "exit_code": 0,
            "results": [],
            "pretty_output": "passed",
            "raw_stdout": "",
            "raw_stderr": "",
        },
    )
    monkeypatch.setattr(
        module,
        "git_add",
        lambda paths, dry_run=True: stage_calls.append((list(paths), dry_run))
        or {
            "dry_run": dry_run,
            "requested_paths": list(paths),
            "staged_paths": [] if dry_run else ["haness/example.py"],
        },
    )
    monkeypatch.setattr(
        module,
        "_write_change_set_evidence",
        lambda *args: "evidence.json",
    )

    result = module.run_change_set(_work_order(confirmed=True), dry_run=False)

    assert result["state"] == "STAGED"
    assert patch_calls == [True, False]
    assert stage_calls == [
        (["haness/example.py"], True),
        (["haness/example.py"], False),
    ]
    assert result["staged_groups"]["source"] == ["haness/example.py"]
    assert result["evidence_path"] == "evidence.json"


def test_failed_tests_reverse_patch_and_do_not_stage(monkeypatch):
    """회귀 테스트 실패 시 patch를 역적용하고 Git 인덱스를 건드리지 않아야 한다."""
    stage_calls = []
    reversed_patches = []
    monkeypatch.setattr(module, "_staged_paths", lambda: [])
    monkeypatch.setattr(
        module,
        "source_patch",
        lambda patch_text, dry_run=True: {
            "dry_run": dry_run,
            "applicable": True,
            "applied": not dry_run,
            "paths": ["haness/example.py"],
            "before_sha256": {"haness/example.py": "before"},
            "after_sha256": {"haness/example.py": "after"},
            "patch_sha256": "patch",
        },
    )
    monkeypatch.setattr(
        module,
        "run_pytest_verification",
        lambda paths, title="": {
            "success": False,
            "exit_code": 1,
            "results": [],
            "pretty_output": "failed",
            "raw_stdout": "",
            "raw_stderr": "",
        },
    )
    monkeypatch.setattr(
        module,
        "_reverse_patch",
        lambda text: reversed_patches.append(text),
    )
    monkeypatch.setattr(
        module,
        "git_add",
        lambda paths, dry_run=True: stage_calls.append((list(paths), dry_run)) or {},
    )
    monkeypatch.setattr(
        module,
        "_write_change_set_evidence",
        lambda *args: "evidence.json",
    )

    result = module.run_change_set(_work_order(confirmed=True), dry_run=False)

    assert result["state"] == "ROLLED_BACK"
    assert reversed_patches == [_work_order()["patch_text"]]
    assert stage_calls == []


def test_public_mcp_tool_routes_json_to_change_set_graph(monkeypatch):
    """MCP 공개 함수는 JSON 변경 세트를 새 LangGraph에 전달해야 한다."""
    expected = {"state": "PLANNED"}
    monkeypatch.setattr(
        orchestrator_tools,
        "_run_change_set",
        lambda payload, dry_run: expected,
    )

    result = asyncio.run(
        orchestrator_tools.run_sps_orchestrator(
            json.dumps(_work_order()),
            dry_run=True,
        )
    )

    assert result is expected


def test_patch_execution_does_not_require_separate_write_approval(monkeypatch):
    """source_patch는 dry-run 통과 후 별도 source_write 승인 없이 진행해야 한다."""
    patch_calls = []
    monkeypatch.setattr(module, "_staged_paths", lambda: [])
    monkeypatch.setattr(
        module,
        "source_patch",
        lambda patch_text, dry_run=True: patch_calls.append(dry_run)
        or {"paths": ["haness/example.py"], "applied": not dry_run},
    )
    monkeypatch.setattr(
        module,
        "run_pytest_verification",
        lambda paths, title="": {"success": True, "exit_code": 0, "results": []},
    )
    monkeypatch.setattr(
        module,
        "git_add",
        lambda paths, dry_run=True: {"staged_paths": list(paths)},
    )
    monkeypatch.setattr(module, "_write_change_set_evidence", lambda *args: "evidence.json")

    result = module.run_change_set(_work_order(confirmed=False), dry_run=False)

    assert result["state"] == "STAGED"
    assert patch_calls == [True, False]


def test_source_write_requires_explicit_approval_before_mutation(monkeypatch):
    """source_write 요청은 승인 값이 없으면 어떤 파일도 쓰지 않아야 한다."""
    work_order = _work_order()
    work_order["writes"] = [
        {"path": "haness/new_agent.py", "content": "VALUE = 1\n", "overwrite": False}
    ]
    work_order["stage_groups"]["source"].append("haness/new_agent.py")
    write_calls = []
    monkeypatch.setattr(
        module,
        "source_write",
        lambda **kwargs: write_calls.append(kwargs),
        raising=False,
    )

    with pytest.raises(ValueError, match="source_write_confirmed=true"):
        module.run_change_set(work_order, dry_run=False)

    assert write_calls == []


def test_approved_source_write_runs_before_tests_and_git_add(monkeypatch):
    """승인된 source_write는 파일 저장 후 pytest와 자동 git add로 이어져야 한다."""
    work_order = _work_order()
    work_order["patch_text"] = ""
    work_order["source_write_confirmed"] = True
    work_order["writes"] = [
        {"path": "haness/new_agent.py", "content": "VALUE = 1\n", "overwrite": False}
    ]
    work_order["stage_groups"]["source"] = ["haness/new_agent.py"]
    write_calls = []
    stage_calls = []
    monkeypatch.setattr(module, "_staged_paths", lambda: [])
    monkeypatch.setattr(
        module,
        "source_write",
        lambda **kwargs: write_calls.append(kwargs) or {"path": kwargs["path"], "sha256": "written"},
    )
    monkeypatch.setattr(
        module,
        "run_pytest_verification",
        lambda paths, title="": {"success": True, "exit_code": 0, "results": []},
    )
    monkeypatch.setattr(
        module,
        "git_add",
        lambda paths, dry_run=True: stage_calls.append((list(paths), dry_run))
        or {"staged_paths": list(paths)},
    )
    monkeypatch.setattr(module, "_write_change_set_evidence", lambda *args: "evidence.json")

    result = module.run_change_set(work_order, dry_run=False)

    assert result["state"] == "STAGED"
    assert [call["path"] for call in write_calls] == ["haness/new_agent.py"]
    assert stage_calls == [(["haness/new_agent.py"], True), (["haness/new_agent.py"], False)]


def test_commit_waits_for_approval_after_source_staging(monkeypatch):
    """commit 요청이 미승인이면 source는 staged 상태로 남고 commit은 실행하지 않는다."""
    work_order = _work_order(confirmed=True)
    work_order["commit"] = {
        "requested": True,
        "confirmed": False,
        "message": "feat: apply SPS change set",
    }
    monkeypatch.setattr(module, "_staged_paths", lambda: [])
    monkeypatch.setattr(module, "source_patch", lambda text, dry_run=True: {"paths": ["haness/example.py"]})
    monkeypatch.setattr(module, "run_pytest_verification", lambda paths, title="": {"success": True})
    monkeypatch.setattr(module, "git_add", lambda paths, dry_run=True: {"staged_paths": list(paths)})
    monkeypatch.setattr(module, "_write_change_set_evidence", lambda *args: "evidence.json")
    commit_calls = []
    monkeypatch.setattr(module, "git_commit", lambda **kwargs: commit_calls.append(kwargs), raising=False)

    result = module.run_change_set(work_order, dry_run=False)

    assert result["commit_state"] == "AWAITING_APPROVAL"
    assert commit_calls == []


def test_confirmed_commit_runs_dry_run_then_commit(monkeypatch):
    """승인된 commit만 정확한 staged 경로로 dry-run 후 실행해야 한다."""
    work_order = _work_order(confirmed=True)
    work_order["commit"] = {"requested": True, "confirmed": True, "message": "feat: SPS change set"}
    monkeypatch.setattr(module, "_staged_paths", lambda: [])
    monkeypatch.setattr(module, "source_patch", lambda text, dry_run=True: {"paths": ["haness/example.py"]})
    monkeypatch.setattr(module, "run_pytest_verification", lambda paths, title="": {"success": True})
    monkeypatch.setattr(module, "git_add", lambda paths, dry_run=True: {"staged_paths": list(paths)})
    monkeypatch.setattr(module, "_write_change_set_evidence", lambda *args: "evidence.json")
    commit_calls = []
    monkeypatch.setattr(
        module,
        "git_commit",
        lambda message, expected_paths, dry_run=True: commit_calls.append(dry_run)
        or {"committed": not dry_run},
        raising=False,
    )

    result = module.run_change_set(work_order, dry_run=False)

    assert result["state"] == "COMMITTED"
    assert commit_calls == [True, False]
