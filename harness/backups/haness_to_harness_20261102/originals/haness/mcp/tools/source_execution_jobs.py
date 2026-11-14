"""장기 Python 실행을 독립 유닛으로 분리하고 제한된 상태 결과를 보존한다."""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
import config
from common.common_function import write_json_atomic

ROOT = Path(config.PROJECT_ROOT).resolve()


def files(job):
    """작업 ID를 검증하여 디렉터리 탈출을 차단한다."""
    if not isinstance(job, str) or not re.fullmatch(r'[0-9a-f]{32}', job):
        raise ValueError('Invalid job_id')
    folder = ROOT / 'harness/memory/source_executions' / job
    return folder / 'request.json', folder / 'result.json'


def status(path, job):
    """종료 기록을 우선하고 죽은 유닛을 영구 실행 중으로 표시하지 않는다."""
    request_path, result_path = files(job)
    request = json.loads(request_path.read_text())
    if (ROOT / path).resolve() != (ROOT / request['path']).resolve():
        raise ValueError('Job source mismatch')
    if result_path.is_file():
        return json.loads(result_path.read_text())
    result = subprocess.run(['systemctl', 'show', request['unit'], '--property=LoadState,ActiveState,Result'], capture_output=True, text=True, timeout=3)
    if result_path.is_file():
        return json.loads(result_path.read_text())
    props = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    state = 'running'
    if result.returncode:
        state = 'status_unavailable'
    elif props.get('LoadState') == 'not-found' or props.get('ActiveState') in {'inactive', 'failed'}:
        state = 'failed'
    return {'job_id': job, 'path': request['path'], 'state': state, 'executed': True,
            'timeout_seconds': request['timeout_seconds'], 'unit': request['unit']}


def submit(plan, source, input_text):
    """승인 완료된 호출만 넘겨받아 10초 이내에 기동 결과를 반환한다."""
    from haness.mcp.tools.multi_persona_tools import _systemd_command
    job = uuid4().hex
    request_path, result_path = files(job)
    unit, command = _systemd_command(['-m', __name__, '--worker', job],
        plan['timeout_seconds'] + config.SPS_WORKER_RESULT_GRACE_SECONDS, 'source-execution')
    command = [arg for arg in command if arg not in {'--wait', '--pipe'}]
    request_path.parent.mkdir(parents=True, mode=0o700)
    # 입력은 프로세스 인자·MCP 결과에 노출하지 않고 제한된 권한으로 저장한다.
    request = {**plan, 'job_id': job, 'unit': unit, 'input_text': input_text,
               'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    write_json_atomic(request_path, request)
    request_path.chmod(0o600)
    try:
        started = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return {**plan, 'executed': True, 'job_id': job, 'unit': unit, 'state': 'status_unavailable'}
    result = {**plan, 'executed': started.returncode == 0, 'job_id': job, 'unit': unit,
              'state': 'running' if started.returncode == 0 else 'failed'}
    if started.returncode:
        from harness.mcp.tools.execution_tools import _trim_output
        result.update(returncode=started.returncode, stderr=_trim_output(started.stderr))
        write_json_atomic(result_path, result)
    return result


def worker(job):
    """제출 후 소스 변경을 거부하고 실행·시간 초과·오류 결과를 남긴다."""
    from harness.mcp.tools.execution_tools import _resolve_source_path, _trim_output
    request_path, result_path = files(job)
    request = json.loads(request_path.read_text())
    result = {k: v for k, v in request.items() if k != 'input_text'}
    result.update(executed=False, state='failed', timed_out=False)
    try:
        source = _resolve_source_path(request['path'])
        if hashlib.sha256(source.read_bytes()).hexdigest() != request['source_sha256']:
            raise ValueError('Source changed after submission')
        seconds = request['timeout_seconds']
        if type(seconds) is not int or not 1 <= seconds <= config.SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS:
            raise ValueError('Invalid execution timeout')
        # 승인 정보는 제출 경계에서 검증되며 여기서는 고정 Python 경로로만 실행한다.
        env = os.environ.copy()
        env['OLLAMA_TIMEOUT'] = str(seconds)
        completed = subprocess.run([str(ROOT / 'venv/bin/python'), str(source)], cwd=ROOT,
            input=request['input_text'], capture_output=True, text=True, timeout=seconds, env=env)
        result.update(executed=True, returncode=completed.returncode,
            state='completed' if completed.returncode == 0 else 'failed',
            stdout=_trim_output(completed.stdout), stderr=_trim_output(completed.stderr))
    except subprocess.TimeoutExpired as exc:
        def decode(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
        result.update(executed=True, state='timed_out', timed_out=True, returncode=None,
            stdout=_trim_output(decode(exc.stdout)), stderr=_trim_output(decode(exc.stderr)))
    except Exception as exc:
        result['stderr'] = _trim_output(str(exc))
    write_json_atomic(result_path, result)
    result_path.chmod(0o600)


if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--worker':
    worker(sys.argv[2])
