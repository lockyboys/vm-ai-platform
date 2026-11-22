"""
self_healer.py — 어디든 끼워 넣을 수 있는 범용 자가 치유(Self-Healing) 모듈
- LLM 우선순위: 1순위 Ollama -> 2순위 Gemini(GEMINI_API_KEY/GOOGLE_API_KEY) -> 3순위 OpenAI
- 도구 연동: SPS Harness MCP(http://127.0.0.1:8000/mcp) + TavilySearch
- 지원 영역:
  1) Python 함수/데코레이터(@self_heal) 및 CLI 명령어(run_command) 자동 진단·패치(.bak 백업)
  2) Playwright 웹 자가 치유(attach_web_sniffer, snapshot_page_dom, autonomous_web_collect):
     - download 이벤트, 팝업 탭, Content-Type: application/pdf 자동 캡처
     - iframe(page.frames) 및 다단계 메뉴(#depth1~3, 판매중지 탭, LLM 힌트) 자율 탐색
"""
# self_healer.py가 오류를 만나 소스를 고치고 재실행하는 순서는 다음과 같습니다.

# 1. 실행 및 실패 감지 (exec_node)
#   대상 함수·명령어·크롤러를 실행한 뒤 예외 발생, 비정상 종료(returncode != 0), 또는 수집 결과 0건이 나오면 치유 단계(heal)로 넘어갑니다.

# 2. 내장 규칙 즉시 복구 (_heuristic_fix)
#  API 호출 전에 먼저 누락된 폴더를 자동 생성(FileNotFoundError)하거나, from __future__ 위치 오류처럼 자주 나는 구문 오류를 .bak 백업 후 즉시 고칩니다.

# 3. SPS Harness MCP 도구 연결
#  use_sps_mcp=True일 때 [http://127.0.0.1:8000/mcp](http://127.0.0.1:8000/mcp)에 접속해 사용 가능한 MCP 도구 목록을 불러옵니다.

# 4.TavilySearch 원인/해결책 조회 (_tavily_search_fix)
#   TAVILY_API_KEY가 있으면 오류 핵심 문구나 대상 도메인으로 최신 해결책 및 대체 URL을 검색합니다.

# 5. LLM 진단 및 수정안 처방 (_llm_diagnose)
#   1순위 Ollama → 2순위 Gemini → 3순위 OpenAI 순으로 가용한 모델에 오류 로그 + 소스 코드(앞 4,000자) + Tavily 결과(+SPS MCP 도구 바인딩)를 전달해 JSON 처방(replace_old, replace_new, fixed_cmd, click_texts, new_url)을 받습니다.

# 6. 원본 백업(.bak) 및 최소 패치 적용 (_apply_heal)
#   처방받은 replace_old가 실제 소스 파일에 정확히 일치할 때만 원본을 *.bak으로 백업한 뒤 replace_new로 치환합니다. 명령어 수정(fixed_cmd)은 위험 명령 필터를 통과한 경우에만 반영합니다.

# 7. 재실행 및 결과 기록 (route → exec)
#   수정된 소스·명령·클릭 힌트를 가지고 max_heal 횟수 내에서 다시 실행하며, 성공하거나 한도에 도달하면 치유 이력을 JSON 리포트로 저장하고 종료합니다.

# 현재 self_healer.py에서 소스와 치유 이력을 기록하는 방식은 두 가지로 나뉩니다.
# 1. 소스 파일 자체 수정 기록 (.bak 백업 후 치환)
#   원본 백업: 수정 직전 shutil.copy2(script_file, script_file.with_suffix(script_file.suffix + ".bak"))로 원본을 파일명.py.bak에 먼저 보존합니다.
#   본문 기록: LLM이 준 replace_old 문자열이 실제 파일 내용(src)에 정확히 일치할 때만 src.replace(replace_old, replace_new, 1)로 1회 치환해 script_file.write_text(..., encoding="utf-8")로 덮어씁니다.
#   (참고: 현재는 코드만 깔끔히 치환하며, 소스 파일 안에 # [Self-Heal] 주석까지는 남기지 않습니다.)
# 2. 치유 과정·결과 로그 기록 (healing_report.json)
#   어떤 오류(error_excerpt) 때문에 어떤 조치(actions), 어떤 SPS MCP 도구(sps_mcp_tools), 어떤 Tavily URL(tavily_urls)을 썼는지는 소스 파일이 아닌 report_path(예: output/healing_report.json)에 JSON 형태로 기록합니다.
from __future__ import annotations

import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import functools
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, TypedDict, TypeVar
from urllib.parse import urljoin

import requests
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

F = TypeVar("F", bound=Callable[..., Any])
_OLLAMA_TIMED_OUT = False


def _load_env_if_needed() -> None:
    """로컬 .env 및 /etc/sps-harness/secrets.env에서 미설정 환경변수를 자동 로드."""
    here = Path(__file__).resolve()
    candidates = [
        Path(".env"),
        here.parent / ".env",
        here.parents[2] / ".env" if len(here.parents) > 2 else here.parent / ".env",
        Path("/etc/sps-harness/secrets.env"),
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.R_OK):
            try:
                for raw in candidate.read_text(encoding="utf-8").splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip().removeprefix("export ").strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v and k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass


_load_env_if_needed()
DANGEROUS_PATTERNS = (r"\brm\s+-rf\s+/\b", r"\bmkfs\b", r"\bdd\s+if=", r":\(\)\s*\{\s*:\|\:&\s*\};:")


class _HealState(TypedDict):
    """LangGraph 치유 루프(exec -> heal -> exec)에서 공유하는 상태 스키마."""
    mode: str
    cmd: str
    script_path: str
    goal: str
    max_heal: int
    use_tavily: bool
    attempt: int
    success: bool
    result: Any
    error_text: str
    healing_log: list[dict[str, Any]]


@dataclass
class HealResult:
    """자가 치유 실행 최종 결과 데이터."""
    success: bool
    attempts: int
    result: Any = None
    error: str = ""
    healing_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WebCaptureState:
    """Playwright 네트워크/팝업/다운로드 감청으로 포착한 PDF URL 및 임시 파일 경로."""
    captured_url: str | None = None
    captured_download_path: Path | None = None


def _is_safe_cmd(cmd: str) -> bool:
    """위험한 시스템 파괴 명령 패턴 포함 여부를 검사."""
    return not any(re.search(pat, cmd) for pat in DANGEROUS_PATTERNS)


def _tavily_search_fix(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """TAVILY_API_KEY가 설정된 경우 오류/도메인 해결책을 웹에서 조회."""
    if not os.getenv("TAVILY_API_KEY"):
        return []
    try:
        tool = TavilySearch(max_results=max_results, topic="general")
        res = tool.invoke({"query": query})
        raw = res.get("results", []) if isinstance(res, dict) else []
        return [
            {"title": str(r.get("title", "")), "url": str(r.get("url", "")), "content": str(r.get("content", ""))[:350]}
            for r in raw
            if isinstance(r, dict)
        ]
    except Exception:
        return []


def _sps_mcp_headers(auth_user: str) -> dict[str, str]:
    """SPS Harness MCP HTTP 엔드포인트 인증 헤더 생성."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-Common-Auth-User": auth_user,
    }
    token = os.getenv("SPS_MCP_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _run_coro_sync(coro: Any) -> Any:
    """이미 실행 중인 asyncio 이벤트 루프(Playwright sync API 등) 내에서도 안전하게 코루틴 실행."""
    try:
        asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)
    except RuntimeError:
        return asyncio.run(coro)


def _load_sps_mcp_tools_langchain(mcp_url: str, auth_user: str) -> list[Any]:
    """langchain-mcp-adapters를 통해 SPS Harness MCP 도구를 LangChain 도구 목록으로 로드."""
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore

        async def _fetch() -> list[Any]:
            client = MultiServerMCPClient(
                {"sps-harness": {"transport": "streamable_http", "url": mcp_url, "headers": _sps_mcp_headers(auth_user)}}
            )
            return await client.get_tools()

        return _run_coro_sync(_fetch())
    except Exception as e:
        print(f"[Self-Heal:MCP] LangChain 어댑터 로드 생략: {e}")
        return []


def _sps_mcp_rpc_list_tools(mcp_url: str, auth_user: str) -> list[str]:
    """어댑터 로드 실패 시 JSON-RPC tools/list 직접 호출로 가용 MCP 도구 이름만 조회."""
    try:
        resp = requests.post(
            mcp_url,
            headers=_sps_mcp_headers(auth_user),
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            timeout=5,
        )
        if resp.status_code != 200:
            return []
        tools = resp.json().get("result", {}).get("tools", [])
        return [str(t.get("name", "")) for t in tools if isinstance(t, dict) and t.get("name")]
    except Exception:
        return []


def _detect_ollama_model(base_url: str) -> str | None:
    """로컬 Ollama에서 임베딩 전용 모델을 제외하고 GPU 채팅 모델을 우선 선택."""
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=1.5)
        if resp.status_code != 200:
            return None
        models = resp.json().get("models", [])
        if not models:
            return None
        env_model = os.getenv("OLLAMA_MODEL", "").strip()
        if env_model:
            return env_model
        names = [str(m.get("name", "")).strip() for m in models if m.get("name")]
        # bge-m3 등 임베딩 전용 모델은 /api/chat 호출 시 400 오류가 나므로 제외
        chat_models = [n for n in names if not any(k in n.lower() for k in ("embed", "bge-", "nomic-", "mxbai-", "e5-"))]
        if not chat_models:
            return None
        # CPU 전용 태그보다 GPU 모델을 우선 선택
        gpu_models = [n for n in chat_models if "-cpu" not in n.lower()]
        return (gpu_models or chat_models)[0]
    except Exception:
        return None


def _ollama_direct_chat(base_url: str, model: str, prompt: str) -> str:
    """LangChain 래퍼 없이 Ollama /api/chat REST API를 직접 호출하는 보조 함수."""
    num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "999"))
    resp = requests.post(
        f"{base_url.rstrip('/')}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": 0, "num_gpu": num_gpu, "num_ctx": 8192, "num_predict": 2048},
        },
        timeout=int(os.getenv("OLLAMA_TIMEOUT", "36000")),
    )
    return str(resp.json().get("message", {}).get("content", "")) if resp.status_code == 200 else ""


def _llm_diagnose(prompt: str, mcp_tools: list[Any] | None = None) -> dict[str, Any]:
    """1순위 AI서버 GPU Ollama -> 2순위 노트북 GPU Ollama -> 3순위 로컬 Ollama -> 4순위 Gemini -> 5순위 OpenAI."""
    global _OLLAMA_TIMED_OUT
    candidates: list[tuple[str, Callable[[], Any]]] = []

    # 1~3순위: Ollama 엔드포인트 순차 탐색 (AI서버 GPU -> 노트북 GPU 리버스 터널 -> 로컬 서버)
    env_ollama_url = os.getenv("OLLAMA_BASE_URL", "").strip()
    laptop_url = os.getenv("OLLAMA_LAPTOP_URL", "http://127.0.0.1:11436").strip()
    ollama_tiers: list[tuple[str, str, int]] = (
        [("지정 Ollama", env_ollama_url, 8192)]
        if env_ollama_url
        else [
            ("AI서버 GPU", "http://10.178.0.8:11434", 8192),
            ("AI서버 GPU(외부)", "http://34.64.144.124:11434", 8192),
            ("노트북 GPU", laptop_url, 4096),
            ("로컬 서버", "http://127.0.0.1:11434", 8192),
        ]
    )
    if not _OLLAMA_TIMED_OUT:
        num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "999"))
        ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "36000"))
        for tier_label, cand_url, ctx_size in ollama_tiers:
            if not cand_url:
                continue
            detected = _detect_ollama_model(cand_url)
            if not detected:
                continue
            def _build_ollama(m: str = detected, u: str = cand_url, c: int = ctx_size) -> Any:
                kwargs: dict[str, Any] = {
                    "model": m,
                    "base_url": u,
                    "temperature": 0,
                    "num_gpu": num_gpu,
                    "num_ctx": c,
                    "num_predict": 2048,
                    "keep_alive": "10m",
                    "client_kwargs": {"timeout": ollama_timeout},
                }
                try:
                    from langchain_ollama import ChatOllama  # type: ignore
                    return ChatOllama(**kwargs)
                except Exception:
                    from langchain_community.chat_models import ChatOllama as LegacyChatOllama  # type: ignore
                    return LegacyChatOllama(model=m, base_url=u, temperature=0, num_gpu=num_gpu, num_ctx=c, keep_alive="10m")
            candidates.append((f"Ollama[{tier_label}] ({detected} @ {cand_url}, num_gpu={num_gpu}/ctx={ctx_size})", _build_ollama))

    # 4순위: Google Gemini (GEMINI_API_KEY 또는 GOOGLE_API_KEY 사용)
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        def _build_gemini() -> Any:
            from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
            return ChatGoogleGenerativeAI(model=gemini_model, google_api_key=gemini_key, temperature=0)
        candidates.append((f"Gemini ({gemini_model})", _build_gemini))

    # 5순위: OpenAI (OPENAI_API_KEY 사용)
    if os.getenv("OPENAI_API_KEY"):
        def _build_openai() -> Any:
            from langchain_openai import ChatOpenAI  # type: ignore
            return ChatOpenAI(model="gpt-4o-mini", temperature=0)
        candidates.append(("OpenAI (gpt-4o-mini)", _build_openai))

    if not candidates:
        print("[Self-Heal:AI] 호출 AI 없음 (Ollama 미실행 및 GEMINI_API_KEY/OPENAI_API_KEY 미설정)")
        return {}

    def _to_text(content: Any) -> str:
        if isinstance(content, list):
            return "\n".join(str(b.get("text", "")) if isinstance(b, dict) else str(b) for b in content)
        if isinstance(content, dict) and "text" in content:
            return str(content["text"])
        return str(content)

    # 후보 AI를 순서대로 호출하며, 오류 또는 JSON 미반환 시 다음 AI로 자동 폴백
    for selected_ai, builder in candidates:
        try:
            print(f"[Self-Heal:AI] 호출 AI = {selected_ai}")
            llm = builder()
            # SPS Harness MCP 도구가 연결되어 있으면 bind_tools로 도구 호출 연동
            if mcp_tools and hasattr(llm, "bind_tools"):
                print(f"[Self-Heal:AI] {selected_ai} + SPS Harness MCP 도구 {len(mcp_tools)}개 호출 중...")
                try:
                    msg = llm.bind_tools(mcp_tools).invoke(prompt)
                    if getattr(msg, "tool_calls", None):
                        tool_map = {t.name: t for t in mcp_tools}
                        outs = []
                        for tc in msg.tool_calls[:3]:
                            t = tool_map.get(tc["name"])
                            if t:
                                try:
                                    res = _run_coro_sync(t.ainvoke(tc["args"])) if hasattr(t, "ainvoke") else t.invoke(tc["args"])
                                    outs.append({"tool": tc["name"], "output": str(res)[:800]})
                                except Exception as te:
                                    outs.append({"tool": tc["name"], "error": str(te)})
                        raw = _to_text(llm.invoke(f"{prompt}\n\n[SPS MCP 결과]\n{json.dumps(outs, ensure_ascii=False)}\n최종 JSON만 반환하세요.").content)
                    else:
                        raw = _to_text(msg.content)
                except Exception:
                    raw = _to_text(llm.invoke(prompt).content)
            else:
                raw = _to_text(llm.invoke(prompt).content)

            # 응답에서 마크다운 펜스 제거 후 모든 '{' 위치에서 유효한 JSON 객체 추출
            cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
            dec = json.JSONDecoder()
            for i, ch in enumerate(cleaned):
                if ch == "{":
                    try:
                        obj, _ = dec.raw_decode(cleaned[i:])
                        if isinstance(obj, dict):
                            if set(obj.keys()) <= {"type", "text", "extras"} and isinstance(obj.get("text"), str):
                                continue
                            print(f"[Self-Heal:AI] {selected_ai} 처방={json.dumps(obj, ensure_ascii=False)[:240]}")
                            return obj
                    except Exception:
                        try:
                            obj = ast.literal_eval(cleaned[i : cleaned.rfind("}") + 1])
                            if isinstance(obj, dict):
                                if set(obj.keys()) <= {"type", "text", "extras"} and isinstance(obj.get("text"), str):
                                    continue
                                print(f"[Self-Heal:AI] {selected_ai} 처방={json.dumps(obj, ensure_ascii=False)[:240]}")
                                return obj
                        except Exception:
                            continue
            print(f"[Self-Heal:AI] {selected_ai} JSON 미반환({cleaned[:120]!r}) -> 다음 AI로 넘어갑니다.")
        except Exception as e:
            print(f"[Self-Heal:AI] {selected_ai} 오류({e}) -> 다음 AI로 넘어갑니다.")
            if selected_ai.startswith("Ollama") and "timed out" in str(e).lower():
                _OLLAMA_TIMED_OUT = True
            continue

    return {}



def _safe_write_patched_source(script_file: Path, patched_code: str, reason: str) -> tuple[bool, str]:
    """수정본의 파이썬 문법을 사전 검증한 뒤, # [Self-Heal 시각] 사유 주석을 기록해 저장."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    heal_comment = f"# [Self-Heal {ts}] {reason.strip()}"
    lines = patched_code.splitlines(keepends=True)

    insert_idx = 0
    if lines and lines[0].startswith("#!"):
        insert_idx = 1
    while insert_idx < len(lines) and (
        lines[insert_idx].lstrip().startswith("from __future__")
        or lines[insert_idx].lstrip().startswith("#")
        or not lines[insert_idx].strip()
    ):
        insert_idx += 1

    annotated = "".join(lines[:insert_idx]) + heal_comment + "\n" + "".join(lines[insert_idx:])
    try:
        if script_file.suffix == ".py":
            compile(annotated, str(script_file), "exec")
    except SyntaxError as se:
        return False, f"문법 검증 실패로 패치 보류({se})"

    shutil.copy2(script_file, script_file.with_suffix(script_file.suffix + ".bak"))
    script_file.write_text(annotated, encoding="utf-8")
    return True, heal_comment


def _heuristic_fix(script_file: Path | None, error_text: str) -> list[str]:
    """LLM 호출 전 자주 발생하는 단순 오류(누락 디렉토리, __future__ 위치)를 즉시 복구."""
    actions: list[str] = []
    m = re.search(r"No such file or directory:\s*'([^']+)'", error_text)
    if m:
        missing = Path(m.group(1))
        missing.parent.mkdir(parents=True, exist_ok=True)
        actions.append(f"누락 경로 생성: {missing.parent}")

    if script_file and script_file.exists():
        code = script_file.read_text(encoding="utf-8")
        if "from __future__ imports must occur at the beginning of the file" in error_text:
            if code.count("#!/usr/bin/env python3") > 1:
                fixed = "#!/usr/bin/env python3" + code.rsplit("#!/usr/bin/env python3", 1)[1]
            else:
                fixed = "from __future__ import annotations\n" + code.replace("from __future__ import annotations\n", "")
            ok_w, msg_w = _safe_write_patched_source(script_file, fixed, "from __future__ 위치 교정 및 중복 제거")
            actions.append(f"from __future__ 교정: {msg_w}" if ok_w else msg_w)
    return actions


class SelfHealer:
    """어디든 import해서 끼워 넣을 수 있는 범용 자가 치유 엔진."""

    def __init__(
        self,
        max_heal: int = 3,
        use_tavily: bool = True,
        use_sps_mcp: bool = True,
        sps_mcp_url: str | None = None,
        sps_auth_user: str | None = None,
        retry_delay_sec: float = 1.0,
        report_path: str | Path | None = None,
        on_heal: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """최대 치유 횟수, Tavily/SPS MCP 사용 여부, 리포트 경로 및 콜백을 초기화."""
        self.max_heal = max_heal
        self.use_tavily = use_tavily
        self.use_sps_mcp = use_sps_mcp
        self.sps_mcp_url = sps_mcp_url or os.getenv("SPS_MCP_URL", "http://127.0.0.1:8000/mcp")
        self.sps_auth_user = sps_auth_user or os.getenv("SPS_AUTH_USER", "jeaje")
        self.retry_delay_sec = retry_delay_sec
        self.report_path = Path(report_path) if report_path else None
        self.on_heal = on_heal

    # ---- 웹/브라우저 자가 치유 유틸리티 ----
    @staticmethod
    def attach_web_sniffer(page: Any, context: Any, cap: WebCaptureState, extra_url_keywords: tuple[str, ...] = ()) -> None:
        """Playwright 페이지에 PDF 응답, 팝업, download 이벤트 캡처를 일괄 부착."""

        def on_response(resp: Any) -> None:
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                u = resp.url.lower()
                if "application/pdf" in ct or ".pdf" in cd or ".pdf" in u or any(k in u for k in extra_url_keywords):
                    cap.captured_url = resp.url
            except Exception:
                pass

        page.on("response", on_response)

        def on_popup(popup: Any) -> None:
            try:
                popup.wait_for_load_state("domcontentloaded", timeout=10000)
                u = popup.url.lower()
                if ".pdf" in u or "pdf" in u or "file" in u:
                    cap.captured_url = popup.url
                popup.on("response", on_response)
            except Exception:
                pass

        context.on("page", on_popup)

        def on_download(dl: Any) -> None:
            try:
                cap.captured_url = dl.url
                tmp = Path("/tmp") / f"hl_dl_{time.time_ns()}.pdf"
                dl.save_as(str(tmp))
                cap.captured_download_path = tmp
            except Exception:
                pass

        page.on("download", on_download)

    @staticmethod
    def snapshot_page_dom(page: Any) -> dict[str, Any]:
        """현재 페이지의 URL, iframe 목록, 보이는 메뉴/버튼 상위 50개를 추출."""
        if not page:
            return {}
        try:
            return page.evaluate(
                """() => ({
                    url: location.href,
                    title: document.title,
                    iframes: Array.from(document.querySelectorAll('iframe')).map(f => f.src).filter(Boolean),
                    visible_controls: Array.from(document.querySelectorAll('a, button, li a, select option'))
                        .map(e => (e.textContent || e.getAttribute('title') || '').replace(/\\s+/g, ' ').trim())
                        .filter(t => t.length > 0 && t.length < 35)
                        .filter((v, i, a) => a.indexOf(v) === i)
                        .slice(0, 50)
                })"""
            )
        except Exception:
            return {}

    @staticmethod
    def autonomous_web_collect(
        page: Any,
        cap: WebCaptureState,
        entry_urls: list[str],
        pdf_dir: Path,
        domain: str,
        insurer_id: str,
        limit: int,
        download: bool,
        click_hints: list[str],
        stream_fn: Callable[[requests.Session, str, Path], tuple[bool, int, int]],
        delay_sec: float = 1.0,
    ) -> list[dict[str, Any]]:
        """iframe(page.frames) + 다단계 메뉴(#depth1~3) + 힌트 클릭으로 PDF를 자율 탐색·저장."""
        pdf_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        def clean_fn(s: str) -> str:
            return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|\r\n]+', "_", s)).strip()[:80]

        def collect_frames(sess: requests.Session, status_label: str) -> None:
            btns: list[tuple[Any, dict[str, Any]]] = []
            for fr in page.frames:
                try:
                    f_btns = fr.evaluate(
                        """() => Array.from(document.querySelectorAll('a, button')).map((el, idx) => ({
                            idx,
                            text: (el.textContent || el.getAttribute('title') || '').replace(/\\s+/g, ' ').trim(),
                            href: el.getAttribute('href') || '',
                            onclick: el.getAttribute('onclick') || ''
                        })).filter(x => (x.text.includes('약관') || x.href.toLowerCase().includes('.pdf') || x.onclick.toLowerCase().includes('down') || x.onclick.toLowerCase().includes('pdf'))
                            && !/위치기반|회원가입|이용약관|계약관리|약관찾기|공시실\\(약관\\)|확인하고 싶어요/.test(x.text))"""
                    )
                    btns.extend([(fr, b) for b in f_btns])
                except Exception:
                    pass

            for fr, b in btns:
                if limit > 0 and len(results) >= limit:
                    return
                seq = len(results) + 1
                fname = f"{seq:03d}_{clean_fn(b['text'] or f'{insurer_id}_{seq}')}_약관.pdf"
                save_path = pdf_dir / fname
                if download and save_path.exists() and save_path.stat().st_size > 1000:
                    results.append({"insurerId": insurer_id, "saleStatus": status_label, "productName": b["text"], "pdfUrl": "cached", "localPath": str(save_path), "bytes": save_path.stat().st_size})
                    continue

                dl_url = b["href"] if ".pdf" in b["href"].lower() else ""
                cap.captured_download_path = None
                if not dl_url:
                    cap.captured_url = None
                    try:
                        fr.evaluate(
                            """(txt) => {
                                const el = Array.from(document.querySelectorAll('a, button')).find(
                                    e => (e.textContent || e.getAttribute('title') || '').replace(/\\s+/g, ' ').trim() === txt
                                );
                                if (el) el.click();
                            }""",
                            b["text"],
                        )
                        for _ in range(16):
                            if cap.captured_url or cap.captured_download_path:
                                break
                            page.wait_for_timeout(250)
                    except Exception:
                        pass
                    dl_url = cap.captured_url or ""

                if cap.captured_download_path and cap.captured_download_path.exists():
                    dl_bytes = cap.captured_download_path.read_bytes()
                    cap.captured_download_path.unlink(missing_ok=True)
                    if dl_bytes[:4] == b"%PDF":
                        save_path.write_bytes(dl_bytes)
                        results.append({"insurerId": insurer_id, "saleStatus": status_label, "productName": b["text"], "pdfUrl": dl_url or "browser_download", "localPath": str(save_path), "bytes": len(dl_bytes)})
                        print(f"  [{insurer_id}:{status_label}] ({seq}) 저장: {fname} ({len(dl_bytes):,} bytes)")
                        continue

                if dl_url and not dl_url.startswith("http"):
                    dl_url = urljoin(f"https://www.{domain}", dl_url)
                if not dl_url or dl_url in seen:
                    continue
                seen.add(dl_url)

                item: dict[str, Any] = {"insurerId": insurer_id, "saleStatus": status_label, "productName": b["text"], "pdfUrl": dl_url}
                if download:
                    ok, _st, size = stream_fn(sess, dl_url, save_path)
                    if ok:
                        item["localPath"] = str(save_path)
                        item["bytes"] = size
                        print(f"  [{insurer_id}:{status_label}] ({seq}) 저장: {fname} ({size:,} bytes)")
                    time.sleep(delay_sec)
                results.append(item)

        for entry_url in list(dict.fromkeys(entry_urls)):
            try:
                page.goto(entry_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
            except Exception:
                continue

            sess = requests.Session()
            sess.headers.update({"User-Agent": page.evaluate("() => navigator.userAgent"), "Referer": entry_url})
            for c in page.context.cookies():
                sess.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

            for hint in click_hints:
                loc = page.locator("a:visible, button:visible").filter(has_text=hint)
                if loc.count() > 0:
                    try:
                        loc.first.click()
                        page.wait_for_timeout(1500)
                    except Exception:
                        pass

            for status_label, tab_kw in (("판매중", "판매상품"), ("판매중지", "판매중지")):
                tab_loc = page.locator("a:visible, button:visible").filter(has_text=tab_kw)
                if status_label == "판매중지" and tab_loc.count() > 0:
                    try:
                        tab_loc.first.click()
                        page.wait_for_timeout(1500)
                    except Exception:
                        pass

                collect_frames(sess, status_label)
                if limit > 0 and len(results) >= limit:
                    break

                d1_cnt = min(page.locator("#depth1 a:visible").count(), 5)
                for d1 in range(d1_cnt):
                    try:
                        page.locator("#depth1 a:visible").nth(d1).click()
                        page.wait_for_timeout(1000)
                        collect_frames(sess, status_label)
                        d2_cnt = min(page.locator("#depth2 a:visible").count(), 5)
                        for d2 in range(d2_cnt):
                            page.locator("#depth2 a:visible").nth(d2).click()
                            page.wait_for_timeout(1000)
                            collect_frames(sess, status_label)
                            d3_cnt = min(page.locator("#depth3 a:visible").count(), 5)
                            for d3 in range(d3_cnt):
                                page.locator("#depth3 a:visible").nth(d3).click()
                                page.wait_for_timeout(1000)
                                collect_frames(sess, status_label)
                                if limit > 0 and len(results) >= limit:
                                    break
                            if limit > 0 and len(results) >= limit:
                                break
                    except Exception:
                        pass
                    if limit > 0 and len(results) >= limit:
                        break
            if results:
                break

        return results

    @staticmethod
    def reload_module(file_path: str | Path, module_name: str = "_healed_module") -> Any | None:
        """자가 치유로 디스크의 소스가 자동 패치된 경우 최신 Python 모듈을 동적 재로드.

        목적: 호출자(앱)가 importlib 로직을 중복 구현하지 않고 SelfHealer를 통해 수정본을 즉시 반영.
        주의: 재로드 대상 파일에 구문 오류가 없어야 하며(_safe_write_patched_source 사전 검증 전제), 실패 시 None 반환.
        """
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if not (spec and spec.loader):
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    # ---- 공통 진단·치유 엔진 ----
    def _apply_heal(self, error_text: str, script_path: str = "", cmd: str = "", goal: str = "") -> dict[str, Any]:
        """휴리스틱 복구 -> SPS MCP 연결 -> TavilySearch -> LLM 진단 -> 최소 소스 패치 순으로 치유 실행."""
        script_file = Path(script_path) if script_path else None
        actions = _heuristic_fix(script_file, error_text)
        new_cmd = cmd

        mcp_tools: list[Any] = []
        mcp_tool_names: list[str] = []
        if self.use_sps_mcp:
            mcp_tools = _load_sps_mcp_tools_langchain(self.sps_mcp_url, self.sps_auth_user)
            if mcp_tools:
                mcp_tool_names = [getattr(t, "name", str(t)) for t in mcp_tools]
                actions.append(f"SPS Harness MCP 도구 {len(mcp_tool_names)}개 연결됨")
            else:
                mcp_tool_names = _sps_mcp_rpc_list_tools(self.sps_mcp_url, self.sps_auth_user)
                if mcp_tool_names:
                    actions.append(f"SPS Harness MCP(RPC) 도구 {len(mcp_tool_names)}개 확인됨")

        tavily_hits: list[dict[str, str]] = []
        if self.use_tavily:
            last_line = error_text.strip().splitlines()[-1] if error_text.strip() else goal
            tavily_hits = _tavily_search_fix(f"python fix {last_line[:120]}")
            if tavily_hits:
                actions.append(f"TavilySearch 참고 {len(tavily_hits)}건 조회")

        # 파일 앞부분만 자르지 않고 오류 줄번호/목표 키워드 주변 핵심 코드를 함께 추출해 LLM에 전달
        src_excerpt = ""
        if script_file and script_file.exists():
            full_src = script_file.read_text(encoding="utf-8")
            if len(full_src) <= 6000:
                src_excerpt = full_src
            else:
                focus_idx = max(full_src.find("def run_generic_healing_crawl"), full_src.find("RUNNERS"))
                m_line = re.search(r"line (\d+)", error_text)
                if m_line:
                    line_pos = sum(len(l) + 1 for l in full_src.splitlines()[: max(0, int(m_line.group(1)) - 25)])
                    focus_idx = max(0, line_pos)
                tail_chunk = full_src[focus_idx : focus_idx + 4500] if focus_idx > 0 else full_src[-4500:]
                src_excerpt = f"{full_src[:1500]}\n\n# ... (핵심 구간) ...\n{tail_chunk}"
        prompt = (
            "실패한 프로그램/함수의 오류를 분석해 최소 수정안을 JSON으로만 반환하세요.\n"
            "가능하면 소스에서 정확히 일치하는 replace_old와 수정 코드 replace_new를 함께 제시하세요.\n"
            f"목표: {goal}\n명령: {cmd}\n오류:\n{error_text[:1800]}\n"
            f"Tavily 참고: {json.dumps(tavily_hits, ensure_ascii=False)[:1000]}\n"
            f"소스:\n{src_excerpt}\n"
            'JSON 형식: {"fixed_cmd": "", "replace_old": "", "replace_new": "", "click_texts": [], "js_actions": [], "new_url": "", "reason": ""}'
        )
        diag = _llm_diagnose(prompt, mcp_tools=mcp_tools)
        if diag:
            if cmd and diag.get("fixed_cmd") and _is_safe_cmd(diag["fixed_cmd"]):
                new_cmd = diag["fixed_cmd"]
                actions.append(f"명령 수정: {new_cmd}")
            if script_file and script_file.exists() and diag.get("replace_old") and diag.get("replace_new"):
                src = script_file.read_text(encoding="utf-8")
                old_s, new_s = str(diag["replace_old"]), str(diag["replace_new"])
                if old_s not in src and old_s.strip() in src:
                    old_s = old_s.strip()
                if old_s in src:
                    reason_str = str(diag.get("reason") or "LLM 자동 수정")
                    ok_w, msg_w = _safe_write_patched_source(script_file, src.replace(old_s, new_s, 1), reason_str)
                    actions.append(f"소스 자동 패치 저장 완료 ({msg_w})" if ok_w else msg_w)
                else:
                    actions.append(f"패치 보류(replace_old 불일치): {str(diag.get('reason') or '')[:80]}")
            elif diag.get("reason") and not diag.get("click_texts") and not diag.get("new_url"):
                actions.append(f"AI 진단: {str(diag.get('reason'))[:100]}")

        if not actions:
            actions.append(f"{self.retry_delay_sec}초 대기 후 재시도")
            time.sleep(self.retry_delay_sec)

        record = {
            "error_excerpt": error_text[:400],
            "actions": actions,
            "sps_mcp_tools": mcp_tool_names[:15],
            "tavily_urls": [h["url"] for h in tavily_hits],
            "new_cmd": new_cmd,
            "click_texts": diag.get("click_texts", []) if isinstance(diag, dict) else [],
            "js_actions": diag.get("js_actions", []) if isinstance(diag, dict) else [],
            "new_url": diag.get("new_url", "") if isinstance(diag, dict) else "",
        }
        if self.on_heal:
            self.on_heal(record)
        return record

    def _save_report(self, result: HealResult) -> None:
        """치유 결과 및 단계별 이력을 report_path JSON 파일로 저장."""
        if not self.report_path:
            return
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps({"success": result.success, "attempts": result.attempts, "error": result.error, "healing_log": result.healing_log}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def run_command(self, cmd: str, script_path: str = "", goal: str = "") -> HealResult:
        """외부 CLI 명령어를 LangGraph 루프(exec -> heal -> exec)로 감싸 자동 복구 실행."""
        def exec_node(state: _HealState) -> dict[str, Any]:
            if not _is_safe_cmd(state["cmd"]):
                return {"success": False, "error_text": "보안 정책상 허용되지 않는 명령입니다."}
            proc = subprocess.run(state["cmd"], shell=True, capture_output=True, text=True, timeout=300)
            return {"success": True, "result": proc.stdout, "error_text": ""} if proc.returncode == 0 else {"success": False, "error_text": proc.stderr or proc.stdout or f"returncode={proc.returncode}"}

        def heal_node(state: _HealState) -> dict[str, Any]:
            rec = self._apply_heal(state["error_text"], state["script_path"], state["cmd"], state["goal"])
            log = list(state["healing_log"])
            log.append({"attempt": state["attempt"] + 1, **rec})
            return {"attempt": state["attempt"] + 1, "cmd": rec["new_cmd"] or state["cmd"], "healing_log": log}

        def route(state: _HealState) -> Literal["heal", "__end__"]:
            return "__end__" if state["success"] or state["attempt"] >= state["max_heal"] else "heal"

        g = StateGraph(_HealState)
        g.add_node("exec", exec_node)
        g.add_node("heal", heal_node)
        g.add_edge(START, "exec")
        g.add_conditional_edges("exec", route, {"heal": "heal", "__end__": END})
        g.add_edge("heal", "exec")
        final = g.compile(checkpointer=MemorySaver()).invoke(
            {"mode": "command", "cmd": cmd, "script_path": script_path, "goal": goal or cmd, "max_heal": self.max_heal, "use_tavily": self.use_tavily, "attempt": 0, "success": False, "result": None, "error_text": "", "healing_log": []},
            config={"configurable": {"thread_id": f"cmd-{time.time_ns()}"}, "recursion_limit": 50},
        )
        res = HealResult(success=final["success"], attempts=final["attempt"] + 1, result=final["result"], error=final["error_text"], healing_log=final["healing_log"])
        self._save_report(res)
        return res

    def run_callable(self, fn: Callable[..., Any], *args: Any, goal: str = "", **kwargs: Any) -> HealResult:
        """Python 함수 호출을 LangGraph 루프로 감싸 예외 발생 시 소스 자동 패치 후 재시도."""
        src_file = inspect.getsourcefile(fn) or ""

        def exec_node(_state: _HealState) -> dict[str, Any]:
            try:
                return {"success": True, "result": fn(*args, **kwargs), "error_text": ""}
            except Exception:
                return {"success": False, "error_text": traceback.format_exc()}

        def heal_node(state: _HealState) -> dict[str, Any]:
            rec = self._apply_heal(state["error_text"], state["script_path"], "", state["goal"])
            log = list(state["healing_log"])
            log.append({"attempt": state["attempt"] + 1, **rec})
            return {"attempt": state["attempt"] + 1, "healing_log": log}

        def route(state: _HealState) -> Literal["heal", "__end__"]:
            return "__end__" if state["success"] or state["attempt"] >= state["max_heal"] else "heal"

        g = StateGraph(_HealState)
        g.add_node("exec", exec_node)
        g.add_node("heal", heal_node)
        g.add_edge(START, "exec")
        g.add_conditional_edges("exec", route, {"heal": "heal", "__end__": END})
        g.add_edge("heal", "exec")
        final = g.compile(checkpointer=MemorySaver()).invoke(
            {"mode": "callable", "cmd": "", "script_path": src_file, "goal": goal or fn.__name__, "max_heal": self.max_heal, "use_tavily": self.use_tavily, "attempt": 0, "success": False, "result": None, "error_text": "", "healing_log": []},
            config={"configurable": {"thread_id": f"fn-{fn.__name__}-{time.time_ns()}"}, "recursion_limit": 50},
        )
        res = HealResult(success=final["success"], attempts=final["attempt"] + 1, result=final["result"], error=final["error_text"], healing_log=final["healing_log"])
        self._save_report(res)
        return res

    def heal_exception(self, exc: BaseException, script_path: str = "", goal: str = "") -> dict[str, Any]:
        """외부 try/except 블록에서 잡은 예외 객체에 대해 1회 진단·치유를 수행."""
        err_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return self._apply_heal(err_text, script_path=script_path, goal=goal)


def self_heal(max_heal: int = 3, use_tavily: bool = True, use_sps_mcp: bool = True, retry_delay_sec: float = 1.0, report_path: str | Path | None = None) -> Callable[[F], F]:
    """일반 Python 함수에 자가 치유 루프를 손쉽게 부착하는 데코레이터."""
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            res = SelfHealer(max_heal=max_heal, use_tavily=use_tavily, use_sps_mcp=use_sps_mcp, retry_delay_sec=retry_delay_sec, report_path=report_path).run_callable(fn, *args, goal=fn.__name__, **kwargs)
            if not res.success:
                raise RuntimeError(f"[self_heal] '{fn.__name__}' 복구 실패 ({res.attempts}회 시도):\n{res.error}")
            return res.result

        return wrapper  # type: ignore[return-value]

    return decorator