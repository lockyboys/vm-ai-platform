"""수집 엔진 확장(2026-10-25) 테스트: 패턴 없는 시드, POST 다운로드.

배경: 자동 탐색기가 만든 프로파일은 (1) 첫 단계 API가 시드 역할을 하므로 HTML 정규식
시드가 필요 없고, (2) 다운로드가 폼 POST인 사이트가 있다. 엔진은 여전히 사이트를 모른다.
주의: 네트워크·DB 연결 없음(가짜 클라이언트).
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("catalog_collector_ext", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = {
    "name": "fake_seedless",
    "base_url": "https://docs.example.org",
    "allowed_hosts": ["docs.example.org"],
    "request": {"method": "POST", "body_format": "form", "headers": {}},
    "seeds": {"pages": [{"url": "/on", "vars": {"flag": "Y", "label": "on"}},
                        {"url": "/off", "vars": {"flag": "N", "label": "off"}}]},
    "steps": [{"url": "/a.do", "body": {"f": "{flag}"}, "list_path": "items", "export": {"file": "FILE"}}],
    "document": {"file_var": "file", "url_template": "/down.asp", "method": "POST",
                 "body": {"file_name": "{file}"}, "subdir_var": "label"},
    "time_limit_seconds": 30000,
}


def test_seedless_profile_is_valid(mod):
    assert mod.validate_profile(copy.deepcopy(BASE))["name"] == "fake_seedless"


def test_seedless_seeds_are_page_vars_without_fetch(mod):
    class NoFetch:
        def get_text(self, path):  # 패턴이 없으면 페이지를 읽지 않아야 한다
            raise AssertionError("seed page must not be fetched")

    assert mod.collect_seeds(NoFetch(), copy.deepcopy(BASE)) == [
        {"flag": "Y", "label": "on"}, {"flag": "N", "label": "off"}]


def test_pattern_without_groups_rejected(mod):
    profile = copy.deepcopy(BASE)
    profile["seeds"]["pattern"] = r"pick\('([^']*)'\)"
    with pytest.raises(ValueError):
        mod.validate_profile(profile)


@pytest.mark.parametrize("document", [
    {"file_var": "file", "url_template": "/d", "method": "DELETE"},          # 허용 안 된 메서드
    {"file_var": "file", "url_template": "/d", "method": "POST", "body": "x"},  # body가 객체 아님
])
def test_bad_document_method_rejected(mod, document):
    profile = copy.deepcopy(BASE)
    profile["document"] = document
    with pytest.raises(ValueError):
        mod.validate_profile(profile)


def test_document_request_renders_post_body(mod):
    url, body = mod.document_request(BASE["document"], "약관 1.pdf")
    assert url == "/down.asp" and body == {"file_name": "약관 1.pdf"}


def test_absolute_document_url_on_allowed_host_is_valid(mod):
    # 문서 서버가 별도 호스트인 사이트(allowed_hosts에 있을 때만 허용)
    profile = copy.deepcopy(BASE)
    profile["allowed_hosts"].append("file.example.org")
    profile["document"]["url_template"] = "https://file.example.org/down.asp"
    profile["document"]["body_charset"] = "cp949"
    assert mod.validate_profile(profile)["document"]["body_charset"] == "cp949"


@pytest.mark.parametrize("url, charset", [
    ("https://evil.example.com/down.asp", "utf-8"),   # 허용 목록 밖 호스트
    ("ftp://file.example.org/down.asp", "utf-8"),      # HTTP(S) 아님
    ("/down.asp", "latin-x"),                          # 알 수 없는 문자셋
])
def test_bad_document_url_or_charset_rejected(mod, url, charset):
    profile = copy.deepcopy(BASE)
    profile["allowed_hosts"].append("file.example.org")
    profile["document"]["url_template"] = url
    profile["document"]["body_charset"] = charset
    with pytest.raises(ValueError):
        mod.validate_profile(profile)


def test_encode_form_with_charset(mod):
    assert mod.encode_form({"file_name": "약관 1.pdf"}, "cp949") == b"file_name=%BE%E0%B0%FC+1.pdf"
    assert mod.encode_form({"file_name": "약관"}, "utf-8") == b"file_name=%EC%95%BD%EA%B4%80"


def test_document_request_get_has_no_body(mod):
    url, body = mod.document_request({"file_var": "f", "url_template": "/d?x={f|q}"}, "a b.pdf")
    assert url == "/d?x=a%20b.pdf" and body is None
