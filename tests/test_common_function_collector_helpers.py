"""수집기에서 common/common_function.py와 루트 config.py로 옮긴 공통 기능의 회귀 테스트.

목적: 사용자 지침 4(공통 설정은 루트 config.py, 공통 함수는 common/common_function.py)에 맞춰
      수집기 내부 함수를 공통 모듈로 옮긴 뒤에도 같은 규칙(잘못된 입력 거부 포함)을 지키는지 확인한다.
주의: 네트워크·DB·systemd는 쓰지 않는다.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

import pytest

import config
from common import common_function as cf


def test_config_has_collector_settings():
    # 상한·크기·디스크 기준을 소스에 박지 않고 루트 config에서 읽어야 한다.
    settings = config.PUBLIC_DOCUMENT_COLLECTOR
    assert settings["max_time_limit_seconds"] == 30000
    assert settings["max_pdf_bytes"] == 512 * 1024 ** 2
    assert settings["min_free_disk_bytes"] == 1024 ** 3
    assert str(settings["profile_dir"]).endswith("FastAPI/LangGraph/Agent_Import_PFDs/profiles")
    assert settings["systemd_run_command"][:3] == ["sudo", "-n", "systemd-run"]


def test_now_kst_iso_has_kst_offset():
    value = cf.now_kst_iso()
    assert value.endswith("+09:00")
    datetime.fromisoformat(value)  # ISO 형식이어야 한다


def test_write_json_atomic_replaces_file(tmp_path):
    target = tmp_path / "status.json"
    cf.write_json_atomic(target, {"state": "RUNNING", "한글": "유지"})
    cf.write_json_atomic(target, {"state": "COMPLETE"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"state": "COMPLETE"}
    assert [p.name for p in tmp_path.iterdir()] == ["status.json"]  # 임시 파일이 남지 않음


@pytest.mark.parametrize("name", ["../약관.pdf", "a/b.pdf", "약관.exe", "", None, ".약관.pdf", "a\\b.pdf", "x" * 201 + ".pdf"])
def test_unsafe_pdf_filename_rejected(name):
    with pytest.raises(ValueError):
        cf.validate_safe_pdf_filename(name)


def test_safe_pdf_filename_allowed():
    assert cf.validate_safe_pdf_filename("약관_31085(04)_20260701.pdf") == "약관_31085(04)_20260701.pdf"


def test_inspect_pdf_file_rejects_html_truncated_empty(tmp_path):
    path = tmp_path / "bad.pdf"
    for content in (b"<html>blocked</html>", b"%PDF-1.4 truncated", b""):
        path.write_bytes(content)
        with pytest.raises(ValueError):
            cf.inspect_pdf_file(path)


def test_inspect_pdf_file_hash(tmp_path):
    data = b"%PDF-1.4\nfixture\n%%EOF\n"
    path = tmp_path / "ok.pdf"
    path.write_bytes(data)
    assert cf.inspect_pdf_file(path) == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
