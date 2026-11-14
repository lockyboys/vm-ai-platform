"""승인된 시간 정책을 모델·SSH 접속 없이 검증하는 회귀 테스트."""
import asyncio
from pathlib import Path
import pytest
import config
from harness.mcp.tools import execution_tools as execution
from haness.mcp.tools import multi_persona_tools as review
from haness.mcp.tools import ssh_execution_tools as ssh


def test_configured_limits():
    # 실행 시간 상한은 없고 입력은 양의 정수여야 한다.
    assert config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS == 3600
    assert config.MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS == 3600
    assert config.SPS_SSH_JOB_TIMEOUT_SECONDS == 3600
    assert config.SPS_GENERAL_UNIT_RUNTIME_SECONDS >= 1


def test_local_long_dry_run_does_not_launch(tmp_path, monkeypatch):
    root = tmp_path / 'FastAPI/LangGraph'
    root.mkdir(parents=True)
    (root / 'sample.py').write_text('print(1)\n')
    monkeypatch.setattr(execution, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(execution, 'EXECUTION_ROOT', root)
    monkeypatch.setattr(execution.subprocess, 'run', lambda *a, **k: pytest.fail('process started'))
    result = execution.mcp_codex_apps_run_python_source('FastAPI/LangGraph/sample.py', timeout_seconds=3600)
    assert result['timeout_seconds'] == 3600
    assert result['executed'] is False
    assert not (tmp_path / 'harness/memory/source_executions').exists()


@pytest.mark.parametrize('purpose,expected', [('orchestrator', 3600), ('persona-source', 3600), ('source-review', 3600), ('source-execution', 3600)])
def test_transient_unit_policy(purpose, expected):
    # 모든 실행 유닛은 무제한 RuntimeMaxSec를 사용한다.
    _, command = review._systemd_command([], 30010, purpose)
    assert f'RuntimeMaxSec={expected}' in command


def test_review_accepts_3600_without_launch(monkeypatch):
    monkeypatch.setattr(review.project_config, 'MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS', 3600)
    result = asyncio.run(review.review_python_source('FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py'))
    assert result['timeout_seconds'] == 3600
    assert 'RuntimeMaxSec=3600' in result['command']
    assert result['executed'] is False


def test_remote_budget_is_not_clamped_to_3000():
    result = ssh.run_remote(path='FastAPI/LangGraph/example.py', ssh_target='gpu', ssh_operation='run', timeout_seconds=3600)
    assert result['timeout_seconds'] == 3600


@pytest.mark.parametrize('value', [True, 0, -1, '3600', None])
def test_invalid_long_budget_rejected(value):
    # bool·문자열·범위 밖 값은 실행 전에 명시적으로 거부한다.
    with pytest.raises(ValueError):
        execution.mcp_codex_apps_run_python_source('FastAPI/LangGraph/audit_gpu_proposed_review.py', timeout_seconds=value)

from types import SimpleNamespace
from haness.mcp.tools import source_execution_jobs as jobs


@pytest.fixture
def job_context(tmp_path, monkeypatch):
    # 격리된 임시 파일과 프로세스 대역으로 실행 기록 계약을 검증한다.
    monkeypatch.setattr(jobs, 'ROOT', tmp_path)
    monkeypatch.setattr(execution, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(execution, 'EXECUTION_ROOT', tmp_path / 'FastAPI/LangGraph')
    source = tmp_path / 'FastAPI/LangGraph/sample.py'
    source.parent.mkdir(parents=True)
    source.write_text('print(1)\n')
    monkeypatch.setattr(jobs.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout='ok', stderr=''))
    return source


def test_long_submission_returns_job_without_input(job_context):
    result = jobs.submit({'path':'FastAPI/LangGraph/sample.py','timeout_seconds':3600}, job_context, 'private input')
    assert result['state'] == 'running'
    assert 'input_text' not in result
    assert (jobs.files(result['job_id'])[0]).stat().st_mode & 0o077 == 0
    jobs.worker(result['job_id'])
    final = jobs.status(result['path'], result['job_id'])
    assert final['state'] == 'completed' and final['returncode'] == 0


def test_worker_timeout_preserves_partial_output(job_context, monkeypatch):
    result = jobs.submit({'path':'FastAPI/LangGraph/sample.py','timeout_seconds':3600}, job_context, '')
    def timeout(*a, **k):
        raise jobs.subprocess.TimeoutExpired('python',3600,output=b'partial')
    monkeypatch.setattr(jobs.subprocess, 'run', timeout)
    jobs.worker(result['job_id'])
    final = jobs.status(result['path'], result['job_id'])
    assert final['state'] == 'timed_out' and final['stdout'] == 'partial'


def test_changed_source_is_not_executed(job_context, monkeypatch):
    result = jobs.submit({'path':'FastAPI/LangGraph/sample.py','timeout_seconds':3600}, job_context, '')
    job_context.write_text('print(2)\n')
    monkeypatch.setattr(jobs.subprocess, 'run', lambda *a, **k: pytest.fail('changed source executed'))
    jobs.worker(result['job_id'])
    assert jobs.status(result['path'],result['job_id'])['executed'] is False


def test_status_rejects_wrong_path(job_context):
    result = jobs.submit({'path':'FastAPI/LangGraph/sample.py','timeout_seconds':3600}, job_context, '')
    with pytest.raises(ValueError):
        jobs.status('FastAPI/LangGraph/other.py',result['job_id'])


def test_missing_unit_is_failed(job_context, monkeypatch):
    result = jobs.submit({'path':'FastAPI/LangGraph/sample.py','timeout_seconds':3600}, job_context, '')
    monkeypatch.setattr(jobs.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='LoadState=not-found\nActiveState=inactive\n',stderr=''))
    assert jobs.status(result['path'],result['job_id'])['state'] == 'failed'


def test_bad_job_id_rejected():
    with pytest.raises(ValueError):
        jobs.files('../escape')
