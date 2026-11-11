"""document_collect 대상 어댑터 테스트 (2026-11-11). 수집기·네트워크 없이 run_collector 주입만 사용."""
from __future__ import annotations

import json

import pytest

from harness.mcp.tools import document_collect_target as target


def test_main_prints_status_json_last_line(capsys):
    """메리츠 사례: 10건 수집 → 마지막 줄 JSON 에 success=10 (부족 판정은 엔진 몫이라 종료 코드 0)."""
    code = target.main(["--collect", "meritz", "메리츠화재", "1000"],
                       run_collector=lambda r: ({"success": 10, "targets": 10}, "s.json", "warn"))
    out = capsys.readouterr()
    assert code == 0
    data = json.loads(out.out.strip().splitlines()[-1])
    assert data["success"] == 10 and data["status_path"] == "s.json"
    assert "warn" in out.err                                  # 수집기 오류 출력은 증빙으로 stderr 에


def test_main_passes_normalized_request():
    seen = []
    target.main(["--collect", "meritz", " 메리츠화재 ", "1000"],
                run_collector=lambda r: (seen.append(r) or ({"success": 1}, "s.json", "")))
    assert seen == [{"name": "meritz", "company_name": "메리츠화재", "expected_min_count": 1000,
                     "document_keyword": "약관"}]


@pytest.mark.parametrize("argv", [
    [], ["--collect"], ["--other", "a", "b", "1"],
    ["--collect", "Meritz", "메리츠화재", "10"],      # 대문자 이름
    ["--collect", "meritz", "", "10"],               # 빈 회사명
    ["--collect", "meritz", "a\nb", "10"],           # 여러 줄
    ["--collect", "meritz", "메리츠화재", "0"],       # 목표 0
    ["--collect", "meritz", "메리츠화재", "-1"],      # 음수
    ["--collect", "meritz", "메리츠화재", "ten"],     # 숫자 아님
])
def test_main_rejects_bad_input(argv, capsys):
    called = []
    assert target.main(argv, run_collector=lambda r: called.append(r)) == 1
    assert called == []                                       # 잘못된 입력이면 수집기를 실행하지 않는다
    assert capsys.readouterr().out == ""


def test_main_reports_collector_failure(capsys):
    def broken(request):
        raise RuntimeError("collector wrote no status.json")
    assert target.main(["--collect", "meritz", "메리츠화재", "10"], run_collector=broken) == 1
    assert "no status.json" in capsys.readouterr().err


def test_validate_request_rejects_bool():
    with pytest.raises(ValueError):
        target.validate_request("meritz", "메리츠화재", True)
