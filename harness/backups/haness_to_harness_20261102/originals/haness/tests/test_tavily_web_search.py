"""Tavily 웹 검색 연결 테스트 (2026-10-25 LuckyBoys: "Tavily 툴로 웹 검색 하도록" → 적용 위치 "둘 다").

1. 공통 함수 common.common_function.web_search
   - 잘못된 질의(빈 문자열·문자열 아님·너무 긺)는 ValueError
   - Tavily 원 응답({"results": [...]} 또는 목록)을 [{"title","url","content"}]로 정리: http(s)만, 중복 제거, 상한 자르기
   - 키(TAVILY_API_KEY)가 없으면 WebSearchUnavailable(값은 읽거나 출력하지 않음)
2. 수집 온보딩(public_document_catalog_collector)
   - start_urls 없이 company_name만 주면 통과(웹 검색은 MCP 호출이 아니라 별도 작업에서)
   - start_urls도 company_name도 없으면 거부(기존 규칙 유지)
   - onboard_worker: start_urls가 비면 검색 → 첫 결과의 호스트와 같은 호스트 URL만 시작 페이지로 넘김(한 호스트 규칙)
   - 검색 결과가 없거나 검색 불가면 탐색을 시작하지 않고 FAILED + 사유를 남김
3. 페르소나 체인 도구(persona_repair_chain)
   - web_search 도구가 공통 함수를 쓰고, 오류도 JSON으로 돌려준다(예외로 그래프를 끊지 않음)
실제 네트워크·Tavily·브라우저·LLM은 쓰지 않는다(search_fn 주입).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from common import common_function as cf

ROOT = Path(__file__).resolve().parents[2]

RAW = {"results": [
    {"title": "공시실", "url": "https://www.example-fire.co.kr/disclosure/terms.do", "content": "약관 공시"},
    {"title": "중복", "url": "https://www.example-fire.co.kr/disclosure/terms.do", "content": "dup"},
    {"title": "판매중지", "url": "https://www.example-fire.co.kr/disclosure/stop.do", "content": "판매중지 약관"},
    {"title": "블로그", "url": "https://blog.other.kr/post/1", "content": "남의 사이트"},
    {"title": "잘못된", "url": "javascript:alert(1)", "content": "x"},
]}


# --- 1. 공통 함수 ------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["", "   ", None, 3, "x" * 501])
def test_web_search_rejects_invalid_query(bad):
    with pytest.raises(ValueError):
        cf.web_search(bad, search_fn=lambda q, n: RAW)


def test_web_search_normalizes_dedups_and_caps():
    out = cf.web_search("example 공시실 약관", max_results=3, search_fn=lambda q, n: RAW)
    assert [r["url"] for r in out] == ["https://www.example-fire.co.kr/disclosure/terms.do",
                                       "https://www.example-fire.co.kr/disclosure/stop.do",
                                       "https://blog.other.kr/post/1"]
    assert set(out[0]) == {"title", "url", "content"}


def test_web_search_accepts_plain_list_response():
    out = cf.web_search("q", search_fn=lambda q, n: RAW["results"][:1])
    assert out[0]["url"].startswith("https://www.example-fire.co.kr/")


def test_web_search_without_key_is_unavailable(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(cf.WebSearchUnavailable):
        cf.web_search("q")


# --- 2. 수집 온보딩 ------------------------------------------------------------------
@pytest.fixture()
def col(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "collector_websearch_t", ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PROFILE_DIR", tmp_path / "profiles")
    (tmp_path / "profiles").mkdir()
    monkeypatch.setattr(module, "output_dir", lambda profile: (tmp_path / "out" / profile["name"]).mkdir(
        parents=True, exist_ok=True) or tmp_path / "out" / profile["name"])
    return module


def test_onboard_accepts_company_name_without_start_urls(col):
    req = col.parse_onboard({"profile": "example_fire_terms", "company_name": "예시화재", "document_keyword": "약관"})
    assert req["start_urls"] == [] and req["company_name"] == "예시화재"


@pytest.mark.parametrize("bad", [
    {"profile": "x_terms"},                                    # 둘 다 없음
    {"profile": "x_terms", "start_urls": []},                  # 빈 목록 + 이름 없음(기존 규칙)
    {"profile": "x_terms", "company_name": ""},
    {"profile": "x_terms", "company_name": "x" * 41},
    {"profile": "x_terms", "company_name": 3},
])
def test_onboard_rejects_missing_or_bad_company_name(col, bad):
    with pytest.raises(ValueError):
        col.parse_onboard(bad)


def _write_request(col, name, **extra):
    out = col.output_dir({"name": name})
    request = {"name": name, "start_urls": [], "document_keyword": "약관", "time_limit_seconds": 60,
               "company_name": "예시화재", **extra}
    (out / "onboard_request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    return out


def test_onboard_worker_searches_and_keeps_first_host_only(col):
    out = _write_request(col, "example_fire_terms")
    seen, queries = [], []
    col.onboard_worker("example_fire_terms", 60,
                       heal_fn=lambda req: seen.append(req) or {"result": "DISCOVERED"},
                       load=lambda name: {"name": name}, worker_fn=lambda p, t: None,
                       search_fn=lambda q, n: queries.append(q) or RAW)
    assert "예시화재" in queries[0] and "약관" in queries[0]
    assert [u["url"] for u in seen[0]["start_urls"]] == ["https://www.example-fire.co.kr/disclosure/terms.do",
                                                        "https://www.example-fire.co.kr/disclosure/stop.do"]
    evidence = json.loads((out / "onboard_search.json").read_text(encoding="utf-8"))
    assert evidence["host"] == "www.example-fire.co.kr" and evidence["query"] == queries[0]


@pytest.mark.parametrize("search_fn,reason", [
    (lambda q, n: {"results": []}, "WEB_SEARCH_NO_RESULT"),
    (lambda q, n: (_ for _ in ()).throw(cf.WebSearchUnavailable("no key")), "WEB_SEARCH_UNAVAILABLE"),
])
def test_onboard_worker_without_search_result_fails_without_discovery(col, search_fn, reason):
    out = _write_request(col, "example_fire_terms")
    seen = []
    report = col.onboard_worker("example_fire_terms", 60, heal_fn=lambda req: seen.append(req) or {},
                                load=lambda name: {}, worker_fn=lambda p, t: None, search_fn=search_fn)
    status = json.loads((out / "status.json").read_text(encoding="utf-8"))
    assert seen == [] and report["result"] == reason and status["state"] == "FAILED" and status["result"] == reason


# --- 3. 페르소나 체인 도구 -----------------------------------------------------------
def test_chain_web_search_tool_returns_json_results_and_errors():
    from haness.mcp.agents import persona_repair_chain as chain

    ok = json.loads(chain.web_search_tool_call("example 공시실", search_fn=lambda q, n: RAW))
    bad = json.loads(chain.web_search_tool_call("", search_fn=lambda q, n: RAW))
    off = json.loads(chain.web_search_tool_call(
        "q", search_fn=lambda q, n: (_ for _ in ()).throw(cf.WebSearchUnavailable("no key"))))
    assert ok["success"] is True and ok["results"][0]["url"].startswith("https://www.example-fire.co.kr/")
    assert bad == {"success": False, "error_code": "INVALID_REQUEST", "error": bad["error"]}
    assert off["error_code"] == "WEB_SEARCH_UNAVAILABLE"


def test_chain_builds_web_search_tool_named_web_search():
    from haness.mcp.agents import persona_repair_chain as chain

    tool = chain.build_web_search_tool()
    assert tool.name == "web_search"
