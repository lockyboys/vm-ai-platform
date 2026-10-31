"""SPS dynamic persona selection connected to scoped source/test tools.

No persona execution order is encoded here. The planner selects the plan from
the existing thirteen prompts; LangGraph carries tool evidence to the next role.
Existing Python review and PARTNER change-set modes remain unchanged.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path, PurePosixPath

import config
from common.common_function import now_kst_iso, write_json_atomic
# 2026-10-25 LuckyBoys: 프롬프트 로드·계획 해석은 common/persona_source.py 공통 클래스로 통합(수리 체인과 공유).
from common.persona_source import PersonaSource
from harness.mcp.tools.patch_tools import source_patch
from haness.mcp.agents.source_partner_agent import _MCP_WRITE_TOOLS, _build_model, _load_sps_mcp_tools
from haness.mcp.tools.multi_persona_tools import PROJECT_ROOT, _systemd_command, _mask_secrets
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode

PERSONAS=frozenset('ORCHESTRATOR ARCHITECT SQL_EXPERT PROMPT_ENGINEER STRATEGIST PARTNER REVIEWER SECURITY TESTER BUG_HUNTER DEVOPS DOCUMENTER TUTOR'.split())


def settings():
    """Read operational limits from the shared root config."""
    return config.SPS_PERSONA_SOURCE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_dir(value):
    """Scope execution to a real app; reject traversal and symlink escapes."""
    if not isinstance(value,str):raise ValueError('target_path required')
    relative=PurePosixPath(value)
    root=Path(PROJECT_ROOT).resolve();apps=root/'haness/apps'
    path=(root/value).resolve()
    if relative.is_absolute() or '..' in relative.parts or apps not in path.parents or not path.is_dir():
        raise ValueError('target_path must identify an app under haness/apps/')
    return path


def parse_plan(text,allowed=PERSONAS):
    """Only model-selected valid roles are accepted; never substitute a fixed plan.

    2026-10-25: 해석 규칙(Gemini 블록·코드펜스·길이·허용 역할 검사)은 공통
    PersonaSource.parse_plan_json으로 옮겼다. 동작(순서·재호출 보존, 잘못되면 예외)은 그대로다.
    """
    return PersonaSource().parse_plan_json(text,allowed,settings()['max_personas'])


class Session:
    """One app-scoped execution: immutable old tests and durable real evidence."""
    def __init__(self,target,evidence,approved=False,baseline_tests=None,owned_tests=None,mcp_tools=None):
        self.target=Path(target).resolve();self.evidence=Path(evidence);self.approved=approved
        self.mcp_tools=list(mcp_tools or [])
        self.roles=[];self.plans=[];self.checks=[];self.patches=[];self.errors=[]
        self.budget_handoffs=[]
        self.calls=0;self.role='ORCHESTRATOR';self.model_checks=0
        self.old_tests={str(p.relative_to(self.target)):sha(p) for p in self.target.rglob('*.test.cjs')}
        if baseline_tests is not None:self.old_tests=dict(baseline_tests)
        self.owned_tests=dict(owned_tests or {})

    def record(self,event,**data):
        self.evidence.mkdir(parents=True,exist_ok=True)
        with (self.evidence/'trace.jsonl').open('a') as stream:
            stream.write(json.dumps({'kst':now_kst_iso(),'role':self.role,'event':event,**data},ensure_ascii=False,default=str)+'\n')

    def file(self,name,exists=False):
        relative=PurePosixPath(name);path=(self.target/name).resolve()
        if relative.is_absolute() or '..' in relative.parts or self.target not in path.parents:
            raise ValueError('file outside target app')
        if exists and not path.is_file():raise ValueError('file not found')
        return path

    def snapshot(self):
        return {str(p.relative_to(self.target)):sha(p) for p in self.target.rglob('*')
                if p.is_file() and self.target in p.resolve().parents}

    def run_checks(self):
        """Execute all discovered Node tests in a new process, without provider secrets."""
        tests=sorted(p for p in self.target.rglob('*.test.cjs') if self.target in p.resolve().parents)
        if not tests:return {'executed':False,'exit_code':None,'error':'no *.test.cjs tests'}
        for name,digest in self.old_tests.items():
            if sha(self.file(name,True))!=digest:raise RuntimeError('existing test changed: '+name)
        command=[shutil.which('node') or 'node','--test','--test-reporter=tap',
                 *[str(p.relative_to(self.target)) for p in tests]]
        before=self.snapshot()
        try:
            done=subprocess.run(command,cwd=self.target,env={'PATH':os.defpath},text=True,
                                capture_output=True,timeout=settings()['check_timeout_seconds'])
            result={'executed':True,'exit_code':done.returncode,'stdout':done.stdout,'stderr':done.stderr}
        except subprocess.TimeoutExpired:result={'executed':True,'exit_code':124,'error':'test timeout'}
        result.update(command=command,snapshot=before)
        if self.snapshot()!=before:result.update(exit_code=125,error='files changed during verification')
        self.checks.append(result);self.record('checks',**result)
        return result

    def create_test(self,name,content):
        """Only approved TESTER calls may add new Node regression files."""
        if not self.approved:raise PermissionError('source_write_confirmed required')
        if self.role!='TESTER':raise PermissionError('only TESTER may add tests')
        path=self.file(name)
        if not name.startswith('tests/') or not name.endswith('.test.cjs') or path.exists():
            raise ValueError('only new tests/*.test.cjs files')
        if len(content.encode())>settings()['max_file_bytes']:raise ValueError('test too large')
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x') as stream:stream.write(content)
        self.record('test_created',path=name,content=content,sha256=sha(path))
        self.owned_tests[name]=sha(path)
        write_json_atomic(self.evidence/'owned_tests.json',self.owned_tests)
        return {'created':True,'path':name}

    def revise_test(self,name,content,reason,expected_sha256):
        """Correct only this job's own test, with provenance and an archived reason.

        Original user tests remain immutable. A resume inherits ownership only
        from a finished job's recorded create events and matching current hash.
        """
        if not self.approved or self.role!='TESTER':raise PermissionError('approved TESTER required')
        path=self.file(name,True)
        if name in self.old_tests or name not in self.owned_tests:
            raise ValueError('only a test created by this job may be revised')
        if not name.startswith('tests/') or not name.endswith('.test.cjs'):
            raise ValueError('test path required')
        if expected_sha256!=self.owned_tests[name] or sha(path)!=expected_sha256:
            raise ValueError('test changed since its recorded creation/revision')
        if not isinstance(reason,str) or len(reason.strip())<20:
            raise ValueError('record evidence explaining why the new test expectation is wrong')
        if not isinstance(content,str) or len(content.encode())>settings()['max_file_bytes']:
            raise ValueError('invalid test content')
        receipt=self.evidence/('test_revision_'+uuid.uuid4().hex);receipt.mkdir(parents=True)
        (receipt/'before.test.cjs').write_bytes(path.read_bytes())
        (receipt/'reason.txt').write_text(reason)
        (receipt/'after.test.cjs').write_text(content)
        path.write_text(content);self.owned_tests[name]=sha(path)
        write_json_atomic(self.evidence/'owned_tests.json',self.owned_tests)
        self.record('test_revised',path=name,reason=reason,sha256=sha(path),evidence=str(receipt))
        return {'revised':True,'path':name,'sha256':sha(path),'evidence':str(receipt)}

    def apply_patch(self,patch):
        """Common source_patch dry-run/apply plus complete tests and guarded rollback."""
        if not self.approved or self.role!='PARTNER':raise PermissionError('approved PARTNER required')
        headers=re.findall(r'^(?:---|\+\+\+) ([ab]/[^\t\n]+)',patch,re.M)
        if not headers or len(headers)%2:raise ValueError('existing-file unified diff required')
        originals={}
        for header in headers:
            path=(Path(PROJECT_ROOT)/header[2:]).resolve()
            if self.target not in path.parents or not path.is_file():raise ValueError('patch outside app')
            if 'tests' in path.relative_to(self.target).parts or path.suffix not in {'.js','.html','.css'}:
                raise ValueError('existing tests are immutable; patch source only')
            originals[path]=path.read_bytes()
        check=source_patch(patch,dry_run=True)
        self.record('patch_dry_run',patch=patch,result=check)
        if not check.get('applicable'):return {'applied':False,'dry_run':check}
        if any(p.read_bytes()!=b for p,b in originals.items()):raise RuntimeError('concurrent edit')
        receipt=self.evidence/('patch_'+uuid.uuid4().hex);receipt.mkdir(parents=True)
        (receipt/'change.patch').write_text(patch)
        for i,(p,b) in enumerate(originals.items()):(receipt/(str(i)+'.before')).write_bytes(b)
        try:
            result=source_patch(patch,dry_run=False)
            if not result.get('applied'):raise RuntimeError('patch not applied')
            verification=self.run_checks()
            if not verification.get('executed') or verification.get('exit_code')!=0:raise RuntimeError('tests failed')
        except Exception as error:
            for p,b in originals.items():p.write_bytes(b)
            self.record('patch_rollback',error=str(error))
            return {'applied':False,'rolled_back':True,'error':str(error)}
        result={'applied':True,'verified':True,'evidence':str(receipt)}
        self.patches.append(result);self.record('patch_applied',**result);return result

    def tools(self,role):
        """Role ownership is enforced at tool binding and write boundaries."""
        @tool
        def list_files()->str:
            """List target-app relative paths."""
            return json.dumps(sorted(self.snapshot()),ensure_ascii=False)
        @tool
        def read_file(path:str,start_line:int=1,max_lines:int=180)->str:
            """Read app text source/tests, returning line numbers and hash."""
            file=self.file(path,True)
            if file.suffix not in {'.js','.cjs','.html','.css','.md','.json','.txt'}:raise ValueError('not text source')
            lines=file.read_text().splitlines();start=max(1,start_line)
            return json.dumps({'sha256':sha(file),'lines':[[i+1,x] for i,x in enumerate(lines)
                    if start<=i+1<start+max(1,min(max_lines,400))]},ensure_ascii=False)
        @tool
        def run_checks()->str:
            """Actually execute all Node tests; return exit code and real output."""
            self.model_checks+=1;result=self.run_checks()
            return json.dumps({**result,'snapshot':None,'stdout':result.get('stdout','')[-16000:]},ensure_ascii=False)
        @tool
        def create_test(path:str,content:str)->str:
            """Add a new regression test; original tests cannot be overwritten."""
            return json.dumps(self.create_test(path,content),ensure_ascii=False)
        @tool
        def revise_test(path:str,content:str,reason:str,expected_sha256:str)->str:
            """Correct only a test created by this job; preserve prior source and evidence-based reason."""
            return json.dumps(self.revise_test(path,content,reason,expected_sha256),ensure_ascii=False)
        @tool
        def apply_source_patch(patch_text:str)->str:
            """Dry-run, apply source diff, run all tests, restore source on failure."""
            return json.dumps(self.apply_patch(patch_text),ensure_ascii=False)
        tools=[list_files,read_file]
        # 모든 페르소나는 동일한 SPS MCP 읽기 도구를 공유한다.
        # 쓰기 도구는 호출 경계 승인과 PARTNER 역할이 동시에 충족될 때만 노출한다.
        tools.extend(mcp_tool for mcp_tool in self.mcp_tools
                     if mcp_tool.name not in _MCP_WRITE_TOOLS or (self.approved and role=='PARTNER'))
        if role in {'TESTER','BUG_HUNTER','PARTNER','REVIEWER','DEVOPS'}:tools.append(run_checks)
        if role=='TESTER':tools.extend([create_test,revise_test])
        if role=='PARTNER':tools.append(apply_source_patch)
        return tools

    def summary(self):
        """A model's prose can never satisfy execution or repair proof."""
        last=self.checks[-1] if self.checks else {}
        verified=bool(self.model_checks and not self.errors and last.get('executed')
                      and last.get('exit_code')==0 and last.get('snapshot')==self.snapshot())
        return {'verified':verified,'plans':self.plans,'roles_completed':self.roles,
                'check_runs':len(self.checks),'last_exit_code':last.get('exit_code'),
                'applied_patches':len(self.patches),'errors':self.errors,
                'budget_handoffs':self.budget_handoffs,
                'autonomous_repair_proven':bool(verified and self.patches and any(
                    x.get('exit_code') not in (0,None) for x in self.checks))}


class State(MessagesState):
    plan:list[str]
    index:int
    role_calls:int


def build_graph(session,model,prompts):
    """Planner chooses the sequence; tools return to the SAME role, not the planner."""
    async def invoke(model,messages):
        session.calls+=1
        if session.calls>settings()['max_llm_calls']:raise RuntimeError('LLM call budget reached')
        return await asyncio.wait_for(model.ainvoke(messages),settings()['model_timeout_seconds'])
    async def planner(state):
        session.role='ORCHESTRATOR'
        # PROMPT_ENGINEER is eligible only for an explicit framework request.
        # Do not mistake framework names in our internal policy for user intent.
        original=str(state['messages'][0].content).lower()
        allowed=PERSONAS if any(name in original for name in ('langchain','langgraph')) else PERSONAS-{'PROMPT_ENGINEER'}
        response=await invoke(model,[SystemMessage(content=prompts['ORCHESTRATOR']+
            '\n역할과 순서는 직접 판단한다. 고정 순서나 전원 호출 금지. JSON만 반환: '
            '{"personas":["ROLE",...]}. 허용 역할: '+','.join(sorted(allowed))+
            '. 최대 '+str(settings()['max_personas'])+'개. 소스 조사/재현 테스트/수정/재검증 목표에 필요한 역할을 고른다. '
            '같은 역할의 재호출도 계획에 넣을 수 있다.'),*state['messages']])
        session.record('planner_response',content=response.content)
        plan=parse_plan(response.content,allowed);session.plans.append(plan)
        session.record('plan',personas=plan,model_output=response.content)
        return {'plan':plan,'index':0,'role_calls':0,'messages':[
            HumanMessage(content='오케스트레이터 실행 계획: '+json.dumps(plan))]}
    async def agent(state):
        role=state['plan'][state['index']];session.role=role
        if state['role_calls']>=settings()['max_role_calls']:raise RuntimeError(role+' tool loop budget reached')
        tools=session.tools(role)
        instructions=prompts[role]+(
            '\n실행 모드다. 앞선 역할 결과와 실제 도구 출력을 공유한다. 앱 상대 경로로 도구를 사용한다. '
            'TESTER는 정상/오류/경계 테스트를 직접 작성/실행한다. 기존 테스트를 완화하지 않는다. '
            '실패를 제품 결함으로 단정하지 말고 테스트 가정을 실제 API 계약과 대조하라. '
            '자신이 새로 만든 테스트의 잘못된 가정은 증빙과 이유를 기록한 revise_test로만 정정할 수 있다. '
            'BUG_HUNTER는 실제 실패의 원인을 조사한다. PARTNER만 앱 소스를 패치하며 화면/엔진 일관성을 확인한다. '
            '실제 실행 없이 통과/수정 완료를 말하지 않는다. 추가 조치 필요 사항을 다음 역할에 전달한다. '
            '전체 소스를 답변에 반복하지 말고 결론은 400자 이내로 쓴다.')
        # Enforce the handoff in code. A provider can still return tool calls
        # after a prose request to stop, even when bind_tools is omitted.
        # Keep every prior result and leave the planner's selected order intact.
        if state['role_calls']>=settings()['max_role_calls']-1:
            session.budget_handoffs.append(role)
            notice='역할 도구 조사 한도에 도달했습니다. 추가 도구는 실행하지 않았습니다. 수집한 증빙과 미확인 사항을 다음 담당에게 인계합니다.'
            session.record('budget_handoff',output=notice,role_calls=state['role_calls'])
            return {'messages':[AIMessage(content=notice)],'role_calls':state['role_calls']}
        response=await invoke(model.bind_tools(tools),
                              [SystemMessage(content=instructions),*state['messages']])
        session.record('model',content=response.content,tool_calls=getattr(response,'tool_calls',[]))
        return {'messages':[response],'role_calls':state['role_calls']+1}
    async def tools(state):
        result=await ToolNode(session.tools(session.role),handle_tool_errors=True).ainvoke(state)
        for message in result['messages']:
            session.record('tool_result',name=message.name,content=message.content)
        return result
    def after_agent(state):
        return 'tools' if getattr(state['messages'][-1],'tool_calls',None) else 'advance'
    def advance(state):
        role=state['plan'][state['index']];session.roles.append(role)
        session.record('role_completed',output=state['messages'][-1].content)
        next_index=state['index']+1
        # Gemini requires a user/tool turn before the next model invocation.
        # Preserve previous role/tool messages and add an explicit handoff turn.
        handoff=[]
        if next_index<len(state['plan']):
            handoff=[HumanMessage(content='다음 담당: '+state['plan'][next_index]+
                '. 앞선 역할의 결과와 실제 도구 증빙을 이어받아 원래 목표의 담당 작업을 수행하라.')]
        return {'index':next_index,'role_calls':0,'messages':handoff}
    def after_advance(state):return 'agent' if state['index']<len(state['plan']) else END
    graph=StateGraph(State)
    for name,node in [('planner',planner),('agent',agent),('tools',tools),('advance',advance)]:graph.add_node(name,node)
    graph.add_edge(START,'planner');graph.add_edge('planner','agent')
    graph.add_conditional_edges('agent',after_agent,{'tools':'tools','advance':'advance'})
    graph.add_edge('tools','agent');graph.add_conditional_edges('advance',after_advance,{'agent':'agent',END:END})
    return graph.compile()


def jobs():return Path(PROJECT_ROOT)/'harness/memory/persona_source_jobs'


def worker_command(job,folder):
    """Reuse the existing worker account/env in an independent transient unit.

    setsid alone does not leave a systemd cgroup. A plain detached Popen child
    dies when its short-lived MCP relay unit exits; the separate unit avoids it.
    """
    unit,command=_systemd_command(['-m','haness.mcp.agents.persona_source_runtime','--worker',job],
                                 settings()['job_timeout_seconds']+10,'persona-source')
    command=[x for x in command if x not in {'--wait','--pipe'}]
    index=command.index(str(Path(PROJECT_ROOT)/'venv/bin/python'))
    log=str(folder/'worker.log')
    command[index:index]=['-p','StandardOutput=append:'+log,'-p','StandardError=append:'+log]
    return unit,command


def job_status(job,folder):
    """A worker killed by timeout or launch failure must never appear RUNNING forever."""
    result=folder/'result.json'
    if result.exists():return json.loads(result.read_text())
    launch=folder/'launch.json'
    if not launch.exists():
        return {'job_id':job,'state':'FAILED','verified':False,'error':'durable worker metadata missing'}
    metadata=json.loads(launch.read_text())
    try:
        process=subprocess.run(['systemctl','show',metadata['unit'],
                                '--property=LoadState,ActiveState,Result'],capture_output=True,text=True,timeout=3)
    except subprocess.TimeoutExpired:return {'job_id':job,'state':'STATUS_UNAVAILABLE','verified':False}
    if result.exists():return json.loads(result.read_text())
    props=dict(line.split('=',1) for line in process.stdout.splitlines() if '=' in line)
    if props.get('LoadState')=='not-found' or props.get('ActiveState') in {'failed','inactive'}:
        failed={'job_id':job,'state':'FAILED','verified':False,'unit_result':props.get('Result'),
                'error':'worker stopped without a final result'}
        write_json_atomic(result,failed);return failed
    if process.returncode:return {'job_id':job,'state':'STATUS_UNAVAILABLE','verified':False}
    lines=(folder/'trace.jsonl').read_text().splitlines() if (folder/'trace.jsonl').exists() else []
    last=json.loads(lines[-1]) if lines else {}
    # Keep status small even when the last event contains a full test source or log.
    # The complete event is retained in trace.jsonl, not repeated in an MCP preview.
    preview={key:last[key] for key in ('kst','role','event','personas','path','name','exit_code') if key in last}
    return {'job_id':job,'state':'RUNNING','events':len(lines),'last_event':preview or None}


def resume_scope(job,target):
    """Recover immutable baselines and owned tests from an auditable failed job."""
    if not isinstance(job,str) or not re.fullmatch('[0-9a-f]{32}',job):raise ValueError('invalid resume job')
    folder=jobs()/job
    if not (folder/'result.json').is_file():raise ValueError('resume requires a finished job')
    result=json.loads((folder/'result.json').read_text())
    if result.get('verified'):raise ValueError('verified job does not need recovery')
    request=json.loads((folder/'request.json').read_text())
    if target_dir(request['target_path'])!=target:raise ValueError('resume target mismatch')
    events=[json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines()]
    checks=[event for event in events if event.get('event')=='checks']
    if not checks:raise ValueError('resume requires an actual check receipt')
    owned={event['path']:event['sha256'] for event in events
           if event.get('event') in {'test_created','test_revised'}}
    baseline=request.get('_baseline_tests')
    if baseline is None:baseline={name:value for name,value in checks[0]['snapshot'].items()
                                 if name.endswith('.test.cjs') and name not in owned}
    validator=Session(target,folder)
    for name,value in {**baseline,**owned}.items():
        if sha(validator.file(name,True))!=value:raise ValueError('resume file changed: '+name)
    failure=checks[-1].get('stdout','')[-16000:]
    return {'resume_job_id':job,'_baseline_tests':baseline,'_owned_tests':owned,'_resume_failure':failure}


def submit(payload,dry_run=True):
    """Plan without LLM in dry-run; start or poll a durable configured worker."""
    if payload.get('job_id'):
        job=str(payload['job_id'])
        if not re.fullmatch('[0-9a-f]{32}',job):raise ValueError('invalid job_id')
        folder=jobs()/job
        if not folder.is_dir():raise ValueError('job not found')
        return job_status(job,folder)
    target=target_dir(payload.get('target_path'));goal=payload.get('goal')
    if not isinstance(goal,str) or not goal.strip() or len(goal)>10000:raise ValueError('goal required, max 10000 chars')
    approved=payload.get('source_write_confirmed',False)
    if not isinstance(approved,bool):raise ValueError('source_write_confirmed must be boolean')
    request={'target_path':str(target.relative_to(Path(PROJECT_ROOT).resolve())),'goal':goal,
             'source_write_confirmed':approved}
    if payload.get('resume_job_id'):request.update(resume_scope(payload['resume_job_id'],target))
    if dry_run:return {'executed':False,'dry_run':True,'dynamic_plan':True,**request}
    job=uuid.uuid4().hex;folder=jobs()/job;folder.mkdir(parents=True)
    write_json_atomic(folder/'request.json',request)
    unit,command=worker_command(job,folder)
    write_json_atomic(folder/'launch.json',{'unit':unit,'started_kst':now_kst_iso()})
    try:
        child=subprocess.run(command,cwd=PROJECT_ROOT,capture_output=True,text=True,timeout=10)
    except subprocess.TimeoutExpired:
        return {'executed':True,'job_id':job,'state':'STATUS_UNAVAILABLE','unit':unit}
    if child.returncode:
        failure={'job_id':job,'state':'FAILED','verified':False,'executed':False,
                 'error':_mask_secrets(child.stderr[-1000:])}
        write_json_atomic(folder/'result.json',failure);return failure
    return {'executed':True,'job_id':job,'state':'RUNNING','unit':unit}


async def run_workflow(session,model,prompts,initial):
    """Replan from actual failed checks, never from a fixed corrective role list."""
    state=initial
    for round_index in range(settings().get('max_plan_rounds',1)):
        graph=build_graph(session,model,prompts)
        state=await graph.ainvoke(state,config={'recursion_limit':settings()['graph_recursion_limit']})
        check=session.run_checks()
        if check.get('executed') and check.get('exit_code')==0:return state
        session.record('replan_needed',round=round_index+1,exit_code=check.get('exit_code'))
        state['messages']=[*state['messages'],HumanMessage(content=
            '마지막 실제 검증이 실패했습니다. 원래 목표를 완수할 담당 역할과 순서를 다시 판단하세요. '
            '제품 결함과 새 테스트의 잘못된 가정을 구분하고 원본 사용자 테스트는 보존하세요. 실제 출력:\n'+
            check.get('stdout',check.get('error',''))[-16000:])]
    return state


async def worker(job):
    """Only path and goal are user input; reuse the thirteen existing role prompts."""
    folder=jobs()/job;request=json.loads((folder/'request.json').read_text())
    # MCP 세션과 tools/list를 페르소나 체인 시작 시 1회만 만들고, 모든 역할에 공유한다.
    mcp_tools=await _load_sps_mcp_tools(source_write_confirmed=bool(request['source_write_confirmed']))
    session=Session(target_dir(request['target_path']),folder,request['source_write_confirmed'],
                    request.get('_baseline_tests'),request.get('_owned_tests'),mcp_tools)
    write_json_atomic(folder/'baseline_tests.json',session.old_tests)
    try:
        # 2026-10-25 LuckyBoys: 프롬프트는 사용자 원문 그대로 — 내장 AdvancedPersonas 대신
        # 공통 원문 파일(config.SPS_PERSONA_PROMPTS, 스킬 references와 sha256 동일)을 쓴다.
        prompts=PersonaSource().load_all(PERSONAS)
        model=_build_model()
        # Bound generation through the shared factory's existing provider fields.
        if hasattr(model,'max_output_tokens'):model.max_output_tokens=settings()['max_output_tokens']
        if hasattr(model,'num_predict'):model.num_predict=settings()['max_output_tokens']
        initial={'messages':[HumanMessage(content=json.dumps({
            'target_path':request['target_path'],'goal':request['goal']},ensure_ascii=False))]}
        if request.get('_resume_failure'):
            initial['messages'].append(HumanMessage(content='이전 작업의 실제 실패 출력입니다. '
                '직접 원인을 판별하고 필요한 역할·순서를 선택하세요.\n'+request['_resume_failure']))
        await asyncio.wait_for(run_workflow(session,model,prompts,initial),settings()['job_timeout_seconds'])
    except Exception as error:
        session.errors.append({'type':type(error).__name__,'message':str(error)})
        session.record('error',**session.errors[-1])
    write_json_atomic(folder/'result.json',{'job_id':job,'state':'COMPLETED',**session.summary()})


if __name__=='__main__' and len(sys.argv)==3 and sys.argv[1]=='--worker':asyncio.run(worker(sys.argv[2]))
