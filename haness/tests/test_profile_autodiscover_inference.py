"""profile_autodiscover 추론 로직 테스트(브라우저·네트워크 없이 가짜 캡처로 검증).

목적: 브라우저가 화면을 클릭하며 기록한 "요청→응답" 순서만 보고, 사이트를 모르는 상태에서
      수집 프로파일(steps / seeds / document)을 스스로 만들어 내는지 확인한다.
가짜 캡처 구조는 실제 공시실에서 흔한 3단계(분류→상품→판매기간·파일) + 폼 POST 다운로드.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py"


@pytest.fixture(scope="module")
def ad():
    spec = importlib.util.spec_from_file_location("profile_autodiscover", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(flag: str, idx: int, file_name: str) -> dict:
    """시작 페이지 1개를 탐색한 캡처(판매중 Y / 판매중지 N)."""
    form = {"PType": "1", "sellFlag": flag, "goodsType": "", "sellType": "", "goodsIndex": ""}
    return {
        "start": {"url": f"/start_{flag}.do", "vars": {"sale_label": "판매중" if flag == "Y" else "판매중지"}},
        "calls": [
            {"path": "/goods/getList.do", "content_type": "application/x-www-form-urlencoded",
             "body": dict(form),
             "response": {"list1": [{"SELL_TYPE": "SA", "GOODS_TYPE": "GA", "SELL_TYPE_NM": "개인"}],
                          "status": {"code": "0000"},
                          "list2": [{"IDX": 1, "GOODS_NAME": "기본"}]}},
            {"path": "/goods/getList2.do", "content_type": "application/x-www-form-urlencoded",
             "body": {**form, "goodsType": "GA", "sellType": "SA"},
             "response": {"list2": [{"IDX": idx, "GOODS_NAME": "상품A"}, {"IDX": idx + 1, "GOODS_NAME": "상품B"}]}},
            {"path": "/goods/getList3.do", "content_type": "application/x-www-form-urlencoded",
             "body": {**form, "goodsType": "GA", "sellType": "SA", "goodsIndex": str(idx)},
             "response": {"list3": [{"SELL_START_DT": "2026-01-01", "FILE_NAME1": "상품A_요약서.pdf",
                                     "FILE_NAME3": file_name}]}},
        ],
        "file_name": file_name,
        "download": {"method": "POST", "url": "https://www.example.co.kr/www/down_chk.asp",
                     "content_type": "application/x-www-form-urlencoded",
                     "body": {"file_name": file_name}},
    }


RUNS = [_run("Y", 2621, "상품A_약관_20261014.pdf"), _run("N", 1500, "상품Z_약관_20200101.pdf")]


def test_find_lists_in_key_order(ad):
    lists = ad.find_lists(RUNS[0]["calls"][0]["response"])
    assert [path for path, _ in lists] == ["list1", "list2"]  # 목록이 아닌 status는 제외


def test_infer_profile_builds_three_linked_steps(ad):
    profile = ad.infer_profile("fake_terms", "https://www.example.co.kr", copy.deepcopy(RUNS))
    steps = profile["steps"]
    assert [s["url"] for s in steps] == ["/goods/getList.do", "/goods/getList2.do", "/goods/getList3.do"]
    assert steps[0]["list_path"] == "list1" and steps[1]["list_path"] == "list2" and steps[2]["list_path"] == "list3"
    # 다음 단계 요청값과 같은 응답 필드가 export로 연결된다
    assert steps[0]["export"] == {"goods_type": "GOODS_TYPE", "sell_type": "SELL_TYPE"}
    assert steps[1]["export"] == {"idx": "IDX"}
    assert steps[2]["body"]["goodsIndex"] == "{idx}" and steps[2]["body"]["goodsType"] == "{goods_type}"
    # 시작 페이지마다 다른 값(sellFlag)은 시드 변수, 같은 값(PType)은 고정값
    assert steps[0]["body"]["sellFlag"] == "{sellFlag}" and steps[0]["body"]["PType"] == "1"
    assert profile["request"]["body_format"] == "form"


def test_infer_profile_seeds_and_document(ad):
    profile = ad.infer_profile("fake_terms", "https://www.example.co.kr", copy.deepcopy(RUNS))
    assert profile["seeds"]["pages"] == [
        {"url": "/start_Y.do", "vars": {"sale_label": "판매중", "sellFlag": "Y"}},
        {"url": "/start_N.do", "vars": {"sale_label": "판매중지", "sellFlag": "N"}}]
    assert "pattern" not in profile["seeds"]
    assert profile["steps"][2]["export"]["doc_file"] == "FILE_NAME3"
    assert profile["document"] == {"file_var": "doc_file", "url_template": "/www/down_chk.asp", "method": "POST",
                                   "body": {"file_name": "{doc_file}"}, "subdir_var": "sale_label"}


def test_parse_form_body_detects_cp949(ad):
    # 국내 ASP 문서 서버는 파일명을 cp949로 보낸다(한화생명 캡처에서 실제 확인한 형태)
    assert ad.parse_form_body("file_name=%BE%E0%B0%FC+1.pdf") == ({"file_name": "약관 1.pdf"}, "cp949")
    assert ad.parse_form_body("file_name=%EC%95%BD%EA%B4%80.pdf") == ({"file_name": "약관.pdf"}, "utf-8")
    assert ad.parse_form_body("") == ({}, "utf-8")


def test_separate_document_host_is_absolute_and_allowed(ad):
    runs = copy.deepcopy(RUNS)
    for run in runs:
        run["download"]["url"] = "https://file.example.co.kr/www/down_chk.asp"
        run["download"]["charset"] = "cp949"
    profile = ad.infer_profile("fake_terms", "https://www.example.co.kr", runs)
    assert profile["document"]["url_template"] == "https://file.example.co.kr/www/down_chk.asp"
    assert profile["document"]["body_charset"] == "cp949"
    assert profile["allowed_hosts"] == ["www.example.co.kr", "file.example.co.kr"]


def test_infer_document_get_query(ad):
    document = ad.infer_document({"method": "GET", "url": "https://x.org/down.do?FilePath=Ins/%EC%95%BD%EA%B4%80%201.pdf",
                                  "body": {}}, "약관 1.pdf", "doc_file")
    assert document["url_template"] == "/down.do?FilePath=Ins/{doc_file|q}" and document.get("method", "GET") == "GET"


# ---- 잘못된 입력 / 추론 불가 ----

def test_chain_broken_is_error(ad):
    runs = copy.deepcopy(RUNS)
    for run in runs:
        run["calls"][2]["body"]["goodsIndex"] = "999999"   # 앞 응답 어디에도 없는 값
    with pytest.raises(ValueError, match="cannot link"):
        ad.infer_profile("fake_terms", "https://www.example.co.kr", runs)


def test_file_not_in_last_response_is_error(ad):
    runs = copy.deepcopy(RUNS)
    runs[0]["file_name"] = "없는파일.pdf"
    with pytest.raises(ValueError, match="file name"):
        ad.infer_profile("fake_terms", "https://www.example.co.kr", runs)


def test_download_without_file_name_is_error(ad):
    with pytest.raises(ValueError, match="download request"):
        ad.infer_document({"method": "POST", "url": "https://x.org/d.asp", "body": {"token": "abc"}},
                          "약관.pdf", "doc_file")


def test_runs_with_different_first_path_rejected(ad):
    runs = copy.deepcopy(RUNS)
    runs[1]["calls"][0]["path"] = "/other.do"
    with pytest.raises(ValueError, match="same first request"):
        ad.infer_profile("fake_terms", "https://www.example.co.kr", runs)


def test_shorter_chain_uses_longest_run_structure(ad):
    # 판매중지 화면이 중간 단계를 건너뛰어도(실제 한화생명) 가장 긴 경로를 구조로 쓰고,
    # 짧은 경로의 시작 페이지는 시드 값만 제공한다(실검증 단계에서 동작 확인).
    runs = copy.deepcopy(RUNS)
    del runs[1]["calls"][1]
    profile = ad.infer_profile("fake_terms", "https://www.example.co.kr", runs)
    assert [s["url"] for s in profile["steps"]] == ["/goods/getList.do", "/goods/getList2.do", "/goods/getList3.do"]
    assert profile["seeds"]["pages"][1]["vars"]["sellFlag"] == "N"


def test_cache_buster_param_is_dropped(ad):
    # 매 요청마다 바뀌는 난수(_r_)는 응답에서 오지 않으므로 휘발성으로 보고 본문에서 뺀다(실제 한화생명).
    runs = copy.deepcopy(RUNS)
    for r_index, run in enumerate(runs):
        for c_index, call in enumerate(run["calls"]):
            call["body"]["_r_"] = f"0.{r_index}{c_index}12345"
    profile = ad.infer_profile("fake_terms", "https://www.example.co.kr", runs)
    assert all("_r_" not in step["body"] for step in profile["steps"])
    assert "_r_" not in profile["seeds"]["pages"][0]["vars"]


def test_file_name_whitespace_is_preserved(ad):
    # 실제 파일명에 연속 공백이 있다("~          _1.pdf"). 원문을 보존해야 다운로드 대상이 맞는다.
    response = {"list3": [{"FILE_NAME3": "상품_약관_20260401~          _1.pdf"}]}
    assert ad.pick_document_value(response, "약관")[2] == "상품_약관_20260401~          _1.pdf"


@pytest.mark.parametrize("name", ["../x", "Hanwha", "", "a" * 65])
def test_bad_profile_name_rejected(ad, name):
    with pytest.raises(ValueError):
        ad.infer_profile(name, "https://www.example.co.kr", copy.deepcopy(RUNS))


def test_pick_document_value_uses_keyword(ad):
    response = RUNS[0]["calls"][2]["response"]
    assert ad.pick_document_value(response, "약관") == ("list3", "FILE_NAME3", "상품A_약관_20261014.pdf")
    assert ad.pick_document_value(response, "사업방법서") is None


def test_score_element_matches_attributes_and_text(ad):
    item = {"SELL_TYPE": "SA", "GOODS_TYPE": "GA", "SELL_TYPE_NM": "개인"}
    element = {"text": "개인 보장성", "attrs": {"data-selltype": "SA", "data-goodstype": "GA", "class": "x"}}
    assert ad.score_element(item, element) == 2
    assert ad.score_element({"GOODS_NAME": "상품A"}, {"text": "상품A", "attrs": {}}) == 1
    assert ad.score_element({"IDX": 1}, {"text": "11", "attrs": {}}) == 0   # 부분 일치는 세지 않음
