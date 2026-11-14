"""Dynamic planning and real execution boundaries; external LLMs are never used."""
import asyncio
import json
from types import SimpleNamespace
import pytest
from langchain_core.messages import AIMessage, HumanMessage


@pytest.fixture
def runtime(monkeypatch):
    from haness.mcp.agents import persona_source_runtime as m
    monkeypatch.setattr(m.config,'SPS_PERSONA_SOURCE',{
        'max_personas':5,'max_role_calls':8,'max_llm_calls':40,
        'check_timeout_seconds':10,'model_timeout_seconds':10,
        'max_file_bytes':24000,'job_timeout_seconds':120,'graph_recursion_limit':100},raising=False)
    return m


@pytest.mark.parametrize('text',['{}','{"personas":[]}','{"personas":["UNKNOWN"]}',
                                '{"personas":[1]}','not json'])
def test_invalid_plan_has_no_fallback_chain(runtime,text):
    """Bad plans fail explicitly instead of falling back to a hard-coded sequence."""
    with pytest.raises((ValueError,TypeError)):runtime.parse_plan(text)


def test_planner_order_and_repeated_roles_are_preserved(runtime):
    """Order comes from the model, including a selected second TESTER invocation."""
    assert runtime.parse_plan('{"personas":["REVIEWER","PARTNER","TESTER","TESTER"]}')==[
        'REVIEWER','PARTNER','TESTER','TESTER']


def test_gemini_typed_content_blocks_are_parsed(runtime):
    """The live provider returns text blocks, not necessarily a string."""
    content=[{'type':'text','text':'{"personas":["TESTER","PARTNER"]}'},
             {'type':'signature','data':'ignored'}]
    assert runtime.parse_plan(content)==['TESTER','PARTNER']


def test_scope_and_symlink_escape(runtime,tmp_path,monkeypatch):
    """The execution scope must remain one app even through a symlink."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    app=tmp_path/'haness/apps/calc';app.mkdir(parents=True)
    for name in ('../out','/etc','haness/apps','config.py'):
        with pytest.raises(ValueError):runtime.target_dir(name)
    session=runtime.Session(app,tmp_path/'receipt',True)
    (app/'escape').symlink_to(tmp_path)
    with pytest.raises(ValueError):session.file('escape/file.js')


def test_write_approval_and_original_tests(runtime,tmp_path):
    """Neither the wrong role nor absent boundary approval may create/overwrite tests."""
    session=runtime.Session(tmp_path,tmp_path/'receipt',False);session.role='TESTER'
    with pytest.raises(PermissionError):session.create_test('tests/new.test.cjs','// intent')
    session.approved=True;session.role='REVIEWER'
    with pytest.raises(PermissionError):session.create_test('tests/new.test.cjs','// intent')
    session.role='TESTER';session.create_test('tests/new.test.cjs','// intent')
    with pytest.raises(ValueError):session.create_test('tests/new.test.cjs','// replaced')
    with pytest.raises(ValueError):session.create_test('engine.js','// wrong path')


def test_role_tool_ownership(runtime,tmp_path):
    """Review cannot write; only TESTER adds tests and only PARTNER patches source."""
    s=runtime.Session(tmp_path,tmp_path/'receipt',True)
    names=lambda role:{t.name for t in s.tools(role)}
    assert 'apply_source_patch' not in names('TESTER')|names('REVIEWER')
    assert 'create_test' not in names('PARTNER')|names('REVIEWER')
    assert 'apply_source_patch' in names('PARTNER') and 'create_test' in names('TESTER')


def test_false_success_and_stale_test_cannot_verify(runtime,tmp_path):
    """No prose or old successful receipt can verify changed source."""
    s=runtime.Session(tmp_path,tmp_path/'receipt',True)
    assert s.summary()['verified'] is False
    s.model_checks=1;s.checks=[{'executed':True,'exit_code':0,'snapshot':s.snapshot()}]
    (tmp_path/'engine.js').write_text('changed')
    assert s.summary()['verified'] is False


def test_patch_failure_restores_original_and_excludes_tests(runtime,tmp_path,monkeypatch):
    """Real post-apply failure restores bytes and cannot be counted as a patch success."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    app=tmp_path/'haness/apps/calc';app.mkdir(parents=True);file=app/'engine.js';file.write_text('old\n')
    session=runtime.Session(app,tmp_path/'receipts',True);session.role='PARTNER'
    def patch(text,dry_run=True):
        if not dry_run:file.write_text('broken\n')
        return {'applicable':True,'applied':not dry_run}
    monkeypatch.setattr(runtime,'source_patch',patch)
    monkeypatch.setattr(session,'run_checks',lambda:{'executed':True,'exit_code':1})
    diff='--- a/haness/apps/calc/engine.js\n+++ b/haness/apps/calc/engine.js\n@@ -1 +1 @@\n-old\n+broken\n'
    result=session.apply_patch(diff)
    assert result['rolled_back'] and file.read_text()=='old\n' and not session.patches


def test_dry_run_does_not_call_model_or_spawn(runtime,tmp_path,monkeypatch):
    """Dry-run validates the request without generating a plan or launching a worker."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    (tmp_path/'haness/apps/calc').mkdir(parents=True)
    monkeypatch.setattr(runtime.subprocess,'Popen',lambda *a,**k:pytest.fail('spawned'))
    result=runtime.submit({'target_path':'haness/apps/calc','goal':'verify'},True)
    assert not result['executed'] and result['dynamic_plan']


def test_graph_handoff_and_tool_return_do_not_replan(runtime,tmp_path):
    """Actual ToolNode returns to the chosen role; the next role receives its evidence."""
    session=runtime.Session(tmp_path,tmp_path/'receipt',True)
    observed=[]
    class Model:
        role=None
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            observed.append(messages)
            n=len(observed)
            if n==1:return AIMessage(content='{"personas":["REVIEWER","TESTER"]}')
            if n==2:return AIMessage(content='',tool_calls=[{'name':'list_files','args':{},'id':'list1'}])
            return AIMessage(content='review completed' if n==3 else 'test handoff received')
    prompts={r:'Role '+r for r in runtime.PERSONAS}
    graph=runtime.build_graph(session,Model(),prompts)
    asyncio.run(graph.ainvoke({'messages':[HumanMessage(content='path and goal only')]},
                             config={'recursion_limit':30}))
    assert session.plans==[['REVIEWER','TESTER']] and session.roles==['REVIEWER','TESTER']
    assert len(observed)==4
    assert any(getattr(m,'tool_call_id',None)=='list1' for m in observed[-1])
    assert any(m.content=='review completed' for m in observed[-1])
    assert not session.summary()['verified']


def test_only_job_owned_tests_can_be_revised(runtime,tmp_path):
    """Wrong new assertions can be corrected without granting access to user tests."""
    (tmp_path/'tests').mkdir();original=tmp_path/'tests/original.test.cjs';original.write_text('// user original')
    s=runtime.Session(tmp_path,tmp_path/'receipt',True);s.role='TESTER'
    with pytest.raises(ValueError):s.revise_test('tests/original.test.cjs','bad','evidence reason long enough',runtime.sha(original))
    s.create_test('tests/owned.test.cjs','// first assumption')
    digest=s.owned_tests['tests/owned.test.cjs']
    with pytest.raises(ValueError):s.revise_test('tests/owned.test.cjs','bad','short',digest)
    with pytest.raises(ValueError):s.revise_test('tests/owned.test.cjs','bad','evidence reason long enough','wrong hash')
    result=s.revise_test('tests/owned.test.cjs','// corrected assertion','Actual API contract contradicts the generated assumption.',digest)
    assert result['revised'] and original.read_text()=='// user original'
    assert list((tmp_path/'receipt').glob('test_revision_*/before.test.cjs'))


def test_status_does_not_embed_large_tool_results(runtime,tmp_path,monkeypatch):
    """Full generated tests/logs stay in trace, preventing MCP's 12000-char truncation."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    folder=runtime.jobs()/('d'*32);folder.mkdir(parents=True)
    (folder/'launch.json').write_text(json.dumps({'unit':'sps-persona-owned'}))
    (folder/'trace.jsonl').write_text(json.dumps({'event':'tool_result','role':'TESTER','content':'x'*100000})+'\n')
    monkeypatch.setattr(runtime.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=0,
        stdout='LoadState=loaded\nActiveState=active\nResult=success\n',stderr=''))
    result=runtime.submit({'job_id':'d'*32},False)
    assert len(json.dumps(result))<2000 and result['last_event']['role']=='TESTER'


def test_resume_uses_verified_provenance_and_rejects_changed_files(runtime,tmp_path,monkeypatch):
    """A failed job can retain ownership of its new tests, never arbitrary existing files."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    app=tmp_path/'haness/apps/calc';(app/'tests').mkdir(parents=True)
    original=app/'tests/original.test.cjs';original.write_text('// user test')
    owned=app/'tests/new.test.cjs';owned.write_text('// generated test')
    folder=runtime.jobs()/('e'*32);folder.mkdir(parents=True)
    (folder/'request.json').write_text(json.dumps({'target_path':'haness/apps/calc'}))
    (folder/'result.json').write_text(json.dumps({'verified':False}))
    events=[{'event':'checks','snapshot':{'tests/original.test.cjs':runtime.sha(original)},'stdout':'failed'},
            {'event':'test_created','path':'tests/new.test.cjs','sha256':runtime.sha(owned)}]
    (folder/'trace.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    recovered=runtime.resume_scope('e'*32,app)
    assert set(recovered['_baseline_tests'])=={'tests/original.test.cjs'}
    assert set(recovered['_owned_tests'])=={'tests/new.test.cjs'}
    owned.write_text('// another session edit')
    with pytest.raises(ValueError,match='changed'):runtime.resume_scope('e'*32,app)


def test_failed_final_check_replans_and_corrects_own_test(runtime,tmp_path,monkeypatch):
    """A controlled fixture reselects roles from logs; no corrective order is hard-coded."""
    monkeypatch.setitem(runtime.config.SPS_PERSONA_SOURCE,'max_plan_rounds',2)
    app=tmp_path/'app';(app/'tests').mkdir(parents=True)
    source=app/'engine.js';source.write_text('module.exports=1;')
    original=app/'tests/original.test.cjs'
    original.write_text("require('node:test')('original',()=>require('node:assert/strict').equal(require('../engine.js'),1));")
    original_bytes=original.read_bytes();s=runtime.Session(app,tmp_path/'receipt',True)
    wrong="require('node:test')('new',()=>require('node:assert/strict').equal(require('../engine.js'),2));"
    correct=wrong.replace('engine.js\'),2','engine.js\'),1')
    class Model:
        calls=0
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            self.calls+=1;n=self.calls
            if n in (1,5):return AIMessage(content='{"personas":["TESTER"]}')
            if n==2:return AIMessage(content='',tool_calls=[{'name':'create_test','args':{
                'path':'tests/generated.test.cjs','content':wrong},'id':'create'}])
            if n in (3,7):return AIMessage(content='',tool_calls=[{'name':'run_checks','args':{},'id':'check'+str(n)}])
            if n==6:return AIMessage(content='',tool_calls=[{'name':'revise_test','args':{
                'path':'tests/generated.test.cjs','content':correct,'reason':'The generated expectation contradicted the real export and original contract.',
                'expected_sha256':s.owned_tests['tests/generated.test.cjs']},'id':'revise'}])
            return AIMessage(content='evidence complete')
    asyncio.run(runtime.run_workflow(s,Model(),{r:'role '+r for r in runtime.PERSONAS},
        {'messages':[HumanMessage(content='verify app')]}))
    assert s.plans==[['TESTER'],['TESTER']] and s.summary()['verified']
    assert original.read_bytes()==original_bytes and source.read_text()=='module.exports=1;'
    assert not s.summary()['autonomous_repair_proven']


def test_real_node_failure_then_pass(runtime,tmp_path):
    """Use a real process: exit codes distinguish failed assertions from passes."""
    app=tmp_path/'app';(app/'tests').mkdir(parents=True)
    (app/'engine.js').write_text('module.exports=1;')
    (app/'tests/basic.test.cjs').write_text("const test=require('node:test');const assert=require('node:assert/strict');test('contract',()=>assert.equal(require('../engine.js'),2));")
    s=runtime.Session(app,tmp_path/'receipt',True)
    assert s.run_checks()['exit_code']!=0
    (app/'engine.js').write_text('module.exports=2;')
    assert s.run_checks()['exit_code']==0


def test_public_orchestrator_dispatch(runtime,monkeypatch):
    """New execution mode is wired to the existing public orchestrator boundary."""
    from haness.mcp.tools import orchestrator_tools
    captured=[]
    monkeypatch.setattr(runtime,'submit',lambda payload,dry_run:captured.append((payload,dry_run)) or {'dynamic_plan':True})
    payload={'mode':'persona_source','target_path':'haness/apps/calc','goal':'verify'}
    result=asyncio.run(orchestrator_tools.run_sps_orchestrator(json.dumps(payload),dry_run=True))
    assert result['dynamic_plan'] and captured[0][0]==payload and captured[0][1] is True

def test_fresh_worker_relays_persona_mode_without_service_reload(runtime,monkeypatch,capsys):
    """A running MCP can relay a persona request through its fresh worker."""
    import io
    from unittest.mock import AsyncMock
    from haness.mcp.tools import orchestrator_tools
    payload={'mode':'persona_source','job_id':'a'*32}
    monkeypatch.setattr(orchestrator_tools.sys,'stdin',io.StringIO(json.dumps({'query':json.dumps(payload)})))
    relay=AsyncMock(return_value={'job_id':'a'*32,'state':'RUNNING'})
    monkeypatch.setattr(orchestrator_tools,'run_sps_orchestrator',relay)
    asyncio.run(orchestrator_tools._worker())
    assert json.loads(capsys.readouterr().out)['state']=='RUNNING'
    relay.assert_awaited_once_with(json.dumps(payload),dry_run=False)


@pytest.mark.parametrize('goal,allowed',[('계산기를 검증',False),('LangGraph 연결 검증',True),('langchain을 검증',True)])
def test_prompt_engineer_eligibility_uses_only_user_goal(runtime,tmp_path,goal,allowed):
    """Only framework requests may select PROMPT_ENGINEER; internal prompts do not count."""
    s=runtime.Session(tmp_path,tmp_path/'receipt',False)
    class Model:
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            if 'JSON만 반환' in messages[0].content:
                return AIMessage(content='{"personas":["PROMPT_ENGINEER"]}')
            return AIMessage(content='design only')
    graph=runtime.build_graph(s,Model(),{r:'LangGraph internal prompt' for r in runtime.PERSONAS})
    run=lambda:asyncio.run(graph.ainvoke({'messages':[HumanMessage(content=goal)]},config={'recursion_limit':20}))
    if allowed:run();assert s.roles==['PROMPT_ENGINEER']
    else:
        with pytest.raises(ValueError,match='ineligible'):run()


def test_last_role_call_reserves_handoff_without_changing_plan(runtime,tmp_path,monkeypatch):
    """A role must hand off evidence when its tool budget is exhausted."""
    monkeypatch.setitem(runtime.config.SPS_PERSONA_SOURCE,'max_role_calls',1)
    s=runtime.Session(tmp_path,tmp_path/'receipt',False)
    class Model:
        calls=0
        def bind_tools(self,tools):pytest.fail('last role call must not bind more tools')
        async def ainvoke(self,messages):
            self.calls+=1
            return AIMessage(content='{"personas":["BUG_HUNTER","TESTER"]}' if self.calls==1 else 'handoff with limitations')
    graph=runtime.build_graph(s,Model(),{r:'role '+r for r in runtime.PERSONAS})
    asyncio.run(graph.ainvoke({'messages':[HumanMessage(content='calculator verification')]},config={'recursion_limit':20}))
    assert s.roles==['BUG_HUNTER','TESTER'] and s.plans==[['BUG_HUNTER','TESTER']]
    assert not s.summary()['verified']


def test_provider_requires_user_turn_between_personas(runtime,tmp_path):
    """Reproduce Gemini's rejection of requests ending in the previous model answer."""
    session=runtime.Session(tmp_path,tmp_path/'receipt',False)
    class Model:
        calls=0
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            if getattr(messages[-1],'type',None)=='ai':
                raise ValueError('Requests ending with a model turn are not supported')
            self.calls+=1
            return AIMessage(content='{"personas":["BUG_HUNTER","TESTER"]}' if self.calls==1 else 'evidence')
    graph=runtime.build_graph(session,Model(),{r:'role '+r for r in runtime.PERSONAS})
    asyncio.run(graph.ainvoke({'messages':[HumanMessage(content='verify calculator')]},config={'recursion_limit':30}))
    assert session.roles==['BUG_HUNTER','TESTER']


def test_job_uses_independent_systemd_unit_not_a_relay_child(runtime,tmp_path,monkeypatch):
    """The relay may exit immediately: the durable worker must live in another unit."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    (tmp_path/'haness/apps/calc').mkdir(parents=True)
    def systemd(arguments,timeout,purpose):
        return 'sps-persona-test',['sudo','-n','systemd-run','--wait','--pipe','--collect',
                                  '--unit=sps-persona-test',str(tmp_path/'venv/bin/python'),*arguments]
    monkeypatch.setattr(runtime,'_systemd_command',systemd,raising=False)
    captured=[]
    monkeypatch.setattr(runtime.subprocess,'Popen',lambda *a,**k:pytest.fail('detached relay child is unsafe'))
    monkeypatch.setattr(runtime.subprocess,'run',lambda command,**kw:captured.append(command) or SimpleNamespace(returncode=0,stdout='',stderr=''))
    result=runtime.submit({'target_path':'haness/apps/calc','goal':'verify'},False)
    assert result['state']=='RUNNING' and '--wait' not in captured[0] and '--pipe' not in captured[0]
    assert any(arg.startswith('StandardOutput=append:') for arg in captured[0])
    assert (runtime.jobs()/result['job_id']/'launch.json').exists()


def test_stopped_worker_is_failed_not_forever_running(runtime,tmp_path,monkeypatch):
    """An externally timed-out or collected unit without a result must report failure."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    folder=runtime.jobs()/('a'*32);folder.mkdir(parents=True)
    (folder/'launch.json').write_text(json.dumps({'unit':'sps-persona-owned-test'}))
    monkeypatch.setattr(runtime.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=0,
        stdout='LoadState=not-found\nActiveState=inactive\nResult=timeout\n',stderr=''))
    result=runtime.submit({'job_id':'a'*32},False)
    assert result['state']=='FAILED' and result['verified'] is False
    assert (folder/'result.json').exists()


@pytest.mark.parametrize('failure',['timeout','budget'])
def test_model_failure_is_persisted_without_killing_next_worker(runtime,tmp_path,monkeypatch,failure):
    """One worker's model timeout/budget error must not prevent an independent next job."""
    import sys
    from pathlib import Path
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    app=tmp_path/'haness/apps/calc';(app/'tests').mkdir(parents=True)
    (app/'tests/pass.test.cjs').write_text("require('node:test')('pass',()=>{});")
    persona_module='FastAPI.LangGraph.multi_persona.multi_persona_agent_gemini'
    monkeypatch.setitem(sys.modules,persona_module,SimpleNamespace(AdvancedPersonas=SimpleNamespace(
        **{r+'_PROMPT':'role '+r for r in runtime.PERSONAS})))
    class Model:
        calls=0
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            self.calls+=1
            if failure=='timeout':await asyncio.sleep(.05)
            if self.calls==1:return AIMessage(content='{"personas":["TESTER"]}')
            if self.calls==2:return AIMessage(content='',tool_calls=[{'name':'run_checks','args':{},'id':'actual'}])
            return AIMessage(content='evidence complete')
    def request(job):
        folder=runtime.jobs()/job;folder.mkdir(parents=True)
        (folder/'request.json').write_text(json.dumps({'target_path':'haness/apps/calc','goal':'verify','source_write_confirmed':False}))
        return folder
    first=request('b'*32)
    monkeypatch.setattr(runtime,'_build_model',lambda:Model())
    monkeypatch.setitem(runtime.config.SPS_PERSONA_SOURCE,'model_timeout_seconds',.005)
    if failure=='budget':monkeypatch.setitem(runtime.config.SPS_PERSONA_SOURCE,'max_llm_calls',1)
    asyncio.run(runtime.worker('b'*32))
    result=json.loads((first/'result.json').read_text())
    assert not result['verified'] and result['errors'][0]['type'] in {'TimeoutError','RuntimeError'}
    failure='healthy'
    monkeypatch.setitem(runtime.config.SPS_PERSONA_SOURCE,'model_timeout_seconds',10)
    monkeypatch.setitem(runtime.config.SPS_PERSONA_SOURCE,'max_llm_calls',40)
    second=request('c'*32);asyncio.run(runtime.worker('c'*32))
    assert json.loads((second/'result.json').read_text())['verified']


def test_patch_and_retest_continue_in_same_graph_job(runtime,tmp_path,monkeypatch):
    """A controlled fixture verifies fix -> fresh Node checks -> next role without restarting graph."""
    monkeypatch.setattr(runtime,'PROJECT_ROOT',tmp_path)
    app=tmp_path/'haness/apps/calc';(app/'tests').mkdir(parents=True)
    source=app/'engine.js';source.write_text('module.exports=1;\n')
    (app/'tests/contract.test.cjs').write_text("const t=require('node:test'),a=require('node:assert/strict');t('contract',()=>a.equal(require('../engine.js'),2));")
    session=runtime.Session(app,tmp_path/'receipt',True)
    def patch(text,dry_run=True):
        if not dry_run:source.write_text('module.exports=2;\n')
        return {'applicable':True,'applied':not dry_run}
    monkeypatch.setattr(runtime,'source_patch',patch)
    diff='--- a/haness/apps/calc/engine.js\n+++ b/haness/apps/calc/engine.js\n@@ -1 +1 @@\n-module.exports=1;\n+module.exports=2;\n'
    class Model:
        calls=0
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            self.calls+=1;n=self.calls
            if n==1:return AIMessage(content='{"personas":["TESTER","PARTNER","TESTER"]}')
            if n in (2,6):return AIMessage(content='',tool_calls=[{'name':'run_checks','args':{},'id':'check'+str(n)}])
            if n==4:return AIMessage(content='',tool_calls=[{'name':'apply_source_patch','args':{'patch_text':diff},'id':'patch1'}])
            return AIMessage(content='evidence handed off')
    graph=runtime.build_graph(session,Model(),{r:'role '+r for r in runtime.PERSONAS})
    asyncio.run(graph.ainvoke({'messages':[HumanMessage(content='verify calculator')]},config={'recursion_limit':40}))
    assert session.roles==['TESTER','PARTNER','TESTER']
    assert [c['exit_code'] for c in session.checks]==[1,0,0]
    assert session.summary()['verified'] and session.summary()['autonomous_repair_proven']


def test_ignored_stop_instruction_cannot_exhaust_entire_job(runtime,tmp_path,monkeypatch):
    """A provider that keeps requesting tools must hand off at the role boundary."""
    monkeypatch.setitem(runtime.config.SPS_PERSONA_SOURCE,'max_role_calls',2)
    session=runtime.Session(tmp_path,tmp_path/'receipt',False)
    class Model:
        calls=0
        def bind_tools(self,tools):return self
        async def ainvoke(self,messages):
            self.calls+=1
            if self.calls==1:return AIMessage(content='{"personas":["BUG_HUNTER","TESTER"]}')
            # Reproduce the live provider returning a tool request even when
            # the old closing prompt asked it to stop calling tools.
            return AIMessage(content='',tool_calls=[
                {'name':'list_files','args':{},'id':'persistent'+str(self.calls)}])
    model=Model()
    graph=runtime.build_graph(session,model,{r:'role '+r for r in runtime.PERSONAS})
    asyncio.run(graph.ainvoke({'messages':[HumanMessage(content='verify tetris')]},
                             config={'recursion_limit':30}))
    assert model.calls==3
    assert session.roles==['BUG_HUNTER','TESTER']
    assert session.summary()['budget_handoffs']==['BUG_HUNTER','TESTER']
    assert not session.summary()['verified']
