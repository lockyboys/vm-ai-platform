"""소스 리뷰 job에서 Tavily 웹 검색을 끄는 기능(선택 B) 시험 (2026-11-12, LuckyBoys 요청).

재현한 문제: router LLM에 Tavily 도구가 붙어 있어 검색 요청 → tools 노드 → router 재호출로
router가 2번 불리고 토큰이 늘었다(Gemini 계산기 job 06c76ff2: 10,082 + 17,192).
확인할 것
1) 리뷰 도구(_review_cli)가 공용 CLI에 --no-web-search를 붙인다(config 값이 False일 때).
2) config 값을 True로 바꾸면 붙이지 않는다(되돌릴 수 있음).
3) 전용 CLI(llm=None)는 이 인자를 모르므로 붙이지 않는다.
4) 잘못된 입력(없는 provider, 문자열 아님)은 거부한다.
5) CLI가 --no-web-search를 받으면 Tavily 도구·tools 노드가 없다 → router는 1번만 호출된다.
   인자가 없으면 이전처럼 동작한다(TAVILY_API_KEY가 있을 때만 도구 생성).
LLM 호출은 없다(그래프만 만들고 실행하지 않음).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import config as project_config
from harness.mcp.tools import multi_persona_tools as tools

ROOT = Path(project_config.PROJECT_ROOT)
CLI = ROOT / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"


@pytest.mark.parametrize("provider", ["gemini", "openai", "claude", "ollama"])
def test_shared_cli_gets_no_web_search(provider):
    """공용 CLI를 쓰는 4종 모두 --provider 뒤에 --no-web-search가 붙는다."""
    _, cli, extra = tools._review_cli(provider)
    assert cli.name == CLI.name
    assert extra == ["--provider", project_config.MULTI_PERSONA_REVIEW_PROVIDERS[provider]["llm"],
                     "--no-web-search"]


def test_config_true_keeps_web_search(monkeypatch):
    """config를 True로 바꾸면 인자를 붙이지 않는다(이전 동작으로 복귀)."""
    monkeypatch.setattr(project_config, "MULTI_PERSONA_REVIEW_WEB_SEARCH", True)
    assert "--no-web-search" not in tools._review_cli("gemini")[2]


def test_dedicated_cli_has_no_flag():
    """전용 CLI(llm=None)는 이 인자를 모르므로 붙이지 않는다."""
    assert tools._review_cli("ollama_gemma")[2] == []


@pytest.mark.parametrize("bad", ["", "GEMINI", "tavily", 3, ["gemini"]])
def test_bad_provider_rejected(bad):
    """잘못된 입력은 리뷰 시작 전에 ValueError로 거부한다."""
    with pytest.raises(ValueError):
        tools._review_cli(bad)


_PROBE = (
    "import json, runpy, sys\n"
    "cli = sys.argv[1]\n"
    "sys.argv = [cli, *sys.argv[2:]]\n"
    "g = runpy.run_path(cli, run_name='probe')\n"  # __main__이 아니므로 리뷰는 실행되지 않음
    "print('PROBE=' + json.dumps({'no_web_search': g['NO_WEB_SEARCH'],"
    " 'tools': len(g['agent_tools']), 'tool_node': g['tool_node'] is not None}))\n"
)


def _probe(*args):
    """CLI 모듈을 실제 인자로 불러 와 웹 검색 도구 상태만 읽는다."""
    done = subprocess.run([sys.executable, "-c", _PROBE, str(CLI), "--provider", "gemini", *args],
                          cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-2000:]
    line = [x for x in done.stdout.splitlines() if x.startswith("PROBE=")][-1]
    return json.loads(line[len("PROBE="):])


def test_cli_no_web_search_removes_tools():
    """--no-web-search면 Tavily 도구와 tools 노드가 없다 → router 재호출 경로가 없다."""
    assert _probe("--no-web-search") == {"no_web_search": True, "tools": 0, "tool_node": False}


def test_cli_default_unchanged():
    """인자가 없으면 이전과 같다: 키가 있으면 도구 1개, 없으면 0개."""
    import os
    state = _probe()
    expected = 1 if os.getenv("TAVILY_API_KEY", "").strip() else 0
    assert state["no_web_search"] is False
    assert state["tools"] == expected and state["tool_node"] is bool(expected)
