"""Run Gemini/Ollama through the existing PARTNER model factory and graph.
Process-local provider selection only. The only tool is a read-only sum probe.

입력(stdin JSON): {"provider": "gemini"|"ollama", "run_id": "<영숫자_->", "tuned": true(선택, ollama만)}

2026-11-01 변경(LuckyBoys 요청, 원본: haness/backups/gemini_timeout_runfile_20261101/):
② 대기 시간을 제공자별로 나눈다.
   gemini → config.SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS / ollama → config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS
③ MCP 연결이 끊겨도 결과를 확인할 수 있게 한다.
   run_id로 결과 파일 이름을 실행 전에 고정 → 시작 즉시 state=running 기록 → 끝나면 같은 파일을
   최종 결과(completed/failed)로 원자적으로 교체한다. 연결이 끊기면 그 파일만 읽으면 된다.
   파일: harness/memory/provider_live_probe_<provider>_<run_id>.json (이미 있으면 거부: 기존 증빙 보존)
공개 함수(테스트 계약, haness/tests/test_probe_partner_timeout_20261031.py):
   timeout_for(config, provider) / evidence_path(provider, run_id) / EVIDENCE_DIR
"""
import asyncio
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

# 결과 파일 폴더. config를 모듈 시작 시 import하면 main()의 제공자 환경변수 지정보다 먼저
# 설정이 읽혀 제공자 선택이 무시되므로, 기존과 같이 이 파일 위치(프로젝트 루트) 기준으로 정한다.
EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "harness/memory"
# run_id는 파일 이름에 들어가므로 경로 문자(/, ..)나 공백이 들어오지 못하게 막는다.
_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
# 제공자 → 루트 config.py의 대기 시간 설정 이름(값은 하드코딩하지 않는다).
_TIMEOUT_SETTING = {
    "gemini": "SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS",
    "ollama": "SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS",
}


def _kst() -> str:
    """증빙 시각은 KST로 남긴다(작업 규칙)."""
    return datetime.now(ZoneInfo("Asia/Seoul")).isoformat()


def timeout_for(cfg, provider: str) -> float:
    """② 제공자에 맞는 대기 시간(초)을 설정에서 읽고 검증한다.

    0 이하·NaN·무한·숫자가 아닌 값은 asyncio.wait_for가 즉시 끊거나 사실상 무한 대기하므로 실행 전에 거부한다.
    """
    if provider not in _TIMEOUT_SETTING:
        raise ValueError(f"unknown provider for timeout: {provider!r}")
    name = _TIMEOUT_SETTING[provider]
    raw = getattr(cfg, name)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {raw!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number > 0, got {raw!r}")
    return value


def _validate_run_id(run_id) -> str:
    """③ run_id 형식 검사. 잘못된 입력(없음·경로 문자·64자 초과·문자열 아님)은 거부한다."""
    if not isinstance(run_id, str) or _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("run_id must match [A-Za-z0-9_-]{1,64}")
    return run_id


def evidence_path(provider: str, run_id) -> Path:
    """③ 실행 전에 결과 파일 경로를 고정한다. 같은 입력이면 항상 같은 경로가 나온다.

    run_id가 잘못되면(경로 문자·빈 값·64자 초과·문자열 아님) 파일을 만들기 전에 ValueError.
    """
    return EVIDENCE_DIR / f"provider_live_probe_{provider}_{_validate_run_id(run_id)}.json"


def _write_atomic(path: Path, value: dict) -> None:
    """임시 파일에 다 쓴 뒤 교체한다. 읽는 쪽이 반쯤 쓴 JSON을 보는 일을 막는다."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _run_with_result_file(path: Path, result: dict, work: Callable[[dict], None]) -> dict:
    """③ running 기록 → work(result) 실행 → completed/failed로 같은 파일을 덮어쓴다.

    work는 result에 측정값을 채운다. 예외가 나도 running으로 방치하지 않고 failed와 오류를 남긴다.
    """
    if path.exists():
        raise FileExistsError(f"run_id already used: {path.name}")  # 기존 증빙 덮어쓰기 금지
    path.parent.mkdir(parents=True, exist_ok=True)
    result.update({"state": "running", "started_kst": _kst()})
    _write_atomic(path, result)
    # 연결이 끊기기 전에 호출자가 파일 위치를 먼저 받을 수 있게 즉시 출력한다.
    print(json.dumps({"evidence": str(path), "state": "running"}), flush=True)
    started = time.monotonic()
    try:
        work(result)
        result["state"] = "completed"
    except Exception as exc:  # 실패도 증빙으로 남긴다(미확인을 성공으로 보고하지 않기)
        result["state"] = "failed"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:2500]
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    result["finished_kst"] = _kst()
    _write_atomic(path, result)
    return result


def main():
    """Execute one explicitly selected provider and preserve its real response."""
    request=json.loads(sys.stdin.read() or "{}")
    provider=request.get("provider")
    if provider not in ("gemini","ollama"):
        raise ValueError("provider must be gemini or ollama")
    path=evidence_path(provider,request.get("run_id"))  # ③ 모델 전에 run_id 검증 + 결과 파일 고정
    run_id=request["run_id"]
    # Only this diagnostic process changes; no .env/config/service files are edited.
    os.environ["SPS_SOURCE_PARTNER_MODEL_PROVIDER"]=provider
    import config
    timeout_seconds=timeout_for(config,provider)  # ② 제공자별 대기 시간(잘못된 값은 여기서 거부)
    from langchain_core.messages import HumanMessage, ToolMessage
    from langchain_core.tools import tool
    from haness.mcp.agents.source_partner_agent import _build_model, build_source_partner_graph

    @tool
    def arithmetic_probe(a:int,b:int)->str:
        """Read-only diagnostic: return the sum of two integers, without storage."""
        return json.dumps({"a":a,"b":b,"sum":a+b})

    async def run():
        model=_build_model()
        if provider=="ollama" and request.get("tuned") is True:
            # Bounded process-local experiment; production defaults are unchanged.
            model.num_ctx=2048
            model.num_predict=128
            model.reasoning=False
            model.keep_alive="10m"
            result["tuning"]={"num_ctx":2048,"num_predict":128,
                              "reasoning":False,"keep_alive":"10m"}
        graph=build_source_partner_graph(model=model,tools=[arithmetic_probe])
        question="연결 진단입니다. arithmetic_probe 도구를 a=17, b=25로 정확히 한 번 호출하고, 그 결과에 근거해 최종 답변에 합계를 적어 주세요. 다른 작업은 하지 마세요."
        result["question"]=question
        result["runtime_class"]=type(model).__name__
        state=await asyncio.wait_for(
            graph.ainvoke({"messages":[HumanMessage(content=question)]},
                          config={"recursion_limit":8}),
            # 2026-10-31: 하드코딩 90초가 Ollama 응답 전에 먼저 끊어 실패로 오판했다.
            # 2026-11-01: 제공자별 루트 config.py 값을 쓴다(timeout_for 참고, Gemini/Ollama 분리).
            timeout=timeout_for(config,provider))
        messages=state.get("messages",[])
        final=messages[-1] if messages else None
        result["answer"]=getattr(final,"content",None)
        result["response_model"]=(getattr(final,"response_metadata",{}) or {}).get("model_name")
        result["usage_metadata"]=getattr(final,"usage_metadata",None)
        result["tool_evidence"]=[
            {"name":m.name,"tool_call_id":m.tool_call_id,"content":m.content}
            for m in messages if isinstance(m,ToolMessage)]
        result["success"]=bool(result["answer"]) and any(
            m["name"]=="arithmetic_probe" and json.loads(m["content"]).get("sum")==42
            for m in result["tool_evidence"])
        result["answer_generation_verified"]=bool(result["answer"])
        result["tool_roundtrip_verified"]=bool(result["tool_evidence"])

    result={"provider":provider,"run_id":run_id,"timeout_seconds":timeout_seconds,
            "configured_model":config.SPS_MAIN_ORCHESTRATOR_MODEL if provider=="gemini"
                else config.SPS_SOURCE_PARTNER_OLLAMA_MODEL,
            "success":False,"source_or_db_mutation":False,
            "probe":"existing _build_model + build_source_partner_graph with read-only arithmetic tool"}
    # ③ running 기록 → 실행 → 같은 파일을 최종 결과로 교체(시간·오류 기록도 이 함수가 맡는다).
    _run_with_result_file(path,result,lambda _result: asyncio.run(run()))
    print(json.dumps({**result,"evidence":str(path)},ensure_ascii=False,default=str))

if __name__=="__main__":
    main()
