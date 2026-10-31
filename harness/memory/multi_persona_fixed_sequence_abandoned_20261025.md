# 미배포 고정 순서 구현 중단

사용자가 역할·실행 순서를 SPS 오케스트레이터에게 맡기도록 정정했습니다. 고정13역할 구현은 로컬 초안만 작성했고 운영 소스에 배포하지 않았습니다. 아래 테스트는 해당 미구현 모듈을 기대하여8건 ImportError가 발생했습니다. 운영 회귀에 남기지 않도록 이 세션에서 새로 만든 동일 내용임을 비교한 뒤 삭제합니다. SPS 프로그램의 실제 자율 실행 성공 증빙이 아닙니다.

```python
"""Contract tests for executable persona handoff; no external model calls."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage


def module():
    from haness.mcp.agents import multi_persona_source_agent
    return multi_persona_source_agent


def test_path_escape_and_non_app_targets_are_rejected(tmp_path, monkeypatch):
    """App-only scope must reject traversal and symlink escapes before execution."""
    m = module(); monkeypatch.setattr(m, 'PROJECT_ROOT', tmp_path)
    app = tmp_path/'haness/apps/calc'; app.mkdir(parents=True)
    for value in ('../outside', 'config.py', 'haness/apps', '/etc'):
        with pytest.raises(ValueError): m.validate_target(value)
    (app/'escape').symlink_to(tmp_path)
    session = m.SourceSession(app, tmp_path/'evidence', False, True)
    with pytest.raises(ValueError): session.file('escape/config.py')


def test_dry_run_does_not_create_model_or_job(tmp_path, monkeypatch):
    """A dry-run is a plan, never a billable model/tool execution."""
    m=module(); monkeypatch.setattr(m,'PROJECT_ROOT',tmp_path)
    (tmp_path/'haness/apps/calc').mkdir(parents=True)
    monkeypatch.setattr(m,'_spawn',lambda *a:pytest.fail('spawn in dry-run'))
    result=m.submit({'target_path':'haness/apps/calc','goal':'verify'},dry_run=True)
    assert not result['executed'] and len(result['roles'])==13


def test_false_success_from_text_cannot_pass(tmp_path):
    """Thirteen optimistic answers without actual tests cannot imply success."""
    m=module(); session=m.SourceSession(tmp_path,tmp_path/'evidence',False,True)
    session.roles=list(m.ROLES)
    assert not session.summary()['verified']
    assert not session.summary()['autonomous_repair_proven']


def test_existing_tests_are_immutable_and_new_test_can_fail(tmp_path):
    """A model may add reproduction tests but cannot erase/change old assertions."""
    m=module(); (tmp_path/'tests').mkdir(); (tmp_path/'tests/a.test.cjs').write_text('old')
    session=m.SourceSession(tmp_path,tmp_path/'evidence',False,True)
    with pytest.raises(ValueError):session.create_test('tests/a.test.cjs','new')
    with pytest.raises(ValueError):session.create_test('engine.js','bad')
    assert session.create_test('tests/new.test.cjs','// purpose\n')['created']


def test_failed_patch_verification_restores_source(tmp_path, monkeypatch):
    """A real failed check after applying a patch must restore the original bytes."""
    m=module(); monkeypatch.setattr(m,'PROJECT_ROOT',tmp_path)
    app=tmp_path/'haness/apps/calc';app.mkdir(parents=True)
    source=app/'engine.js';source.write_text('old\n')
    session=m.SourceSession(app,tmp_path/'evidence',False,True)
    def patch(text,dry_run=True):
        if not dry_run:source.write_text('new\n')
        return {'applicable':True,'applied':not dry_run}
    monkeypatch.setattr(m,'source_patch',patch)
    monkeypatch.setattr(session,'run_checks',lambda:{'exit_code':1,'executed':True})
    patch_text='--- a/haness/apps/calc/engine.js\n+++ b/haness/apps/calc/engine.js\n@@ -1 +1 @@\n-old\n+new\n'
    result=session.apply_patch(patch_text)
    assert result['rolled_back'] and source.read_text()=='old\n'
    assert not session.changes


def test_approval_is_required_and_dry_patch_never_applies(tmp_path,monkeypatch):
    """Approval comes from the API boundary; a model cannot manufacture it."""
    m=module(); session=m.SourceSession(tmp_path,tmp_path/'evidence',False,False)
    with pytest.raises(PermissionError):session.create_test('tests/new.test.cjs','// test')


def test_shared_graph_calls_all_roles_and_passes_results(tmp_path):
    """Actual graph state, not separate prompts, must carry prior persona answers."""
    m=module(); session=m.SourceSession(tmp_path,tmp_path/'evidence',False,True)
    observed=[]
    class Model:
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            observed.append(messages)
            return AIMessage(content='ROLE_RESULT_'+str(len(observed)))
    graph=m.build_graph(session,Model(),{r:'role '+r for r in m.ROLES})
    result=asyncio.run(graph.ainvoke({'messages':[]},config={'recursion_limit':40}))
    assert session.roles==list(m.ROLES)
    assert len(observed)==13
    assert any('ROLE_RESULT_1' in str(x.content) for x in observed[1])
    assert not session.summary()['verified']


def test_public_boundary_routes_to_durable_execution(monkeypatch):
    """The existing orchestrator must expose the new execution mode, not a standalone demo."""
    m=module();from haness.mcp.tools import orchestrator_tools
    captured=[]
    monkeypatch.setattr(m,'submit',lambda payload,dry_run:captured.append((payload,dry_run)) or {'state':'PLANNED'})
    payload={'mode':'multi_persona_source','target_path':'haness/apps/calc','goal':'verify'}
    answer=asyncio.run(orchestrator_tools.run_sps_orchestrator(json.dumps(payload),dry_run=True))
    assert answer['state']=='PLANNED' and captured[0][1] is True
```
