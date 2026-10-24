"""8003 CLI의 입력·오류·dry-run을 검증하며 실제 모델은 호출하지 않는다."""
import io
import json
from urllib.error import HTTPError, URLError
import pytest
from FastAPI.LangGraph import agent_cli as cli

def test_empty_query_is_rejected_before_network(monkeypatch):
    monkeypatch.setattr(cli, "urlopen", lambda *a, **k: pytest.fail("network must not run"))
    with pytest.raises(ValueError):
        cli.make_payload("  ")

def test_long_query_is_rejected():
    with pytest.raises(ValueError):
        cli.make_payload("x" * 12001)

def test_dry_run_requires_no_credentials(monkeypatch, capsys):
    monkeypatch.setattr(cli, "get_token", lambda *a: pytest.fail("no token for dry run"))
    assert cli.main(["--query", "17+25", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["payload"]["query"] == "17+25"

def test_http_401_has_safe_error(monkeypatch):
    def fail(*a, **k):
        raise HTTPError("http://localhost", 401, "Unauthorized", {}, None)
    monkeypatch.setattr(cli, "urlopen", fail)
    with pytest.raises(RuntimeError, match="401"):
        cli.ask(cli.make_payload("hello"), "private-token")

def test_connection_error(monkeypatch):
    def fail(*a, **k):
        raise URLError("connection refused")
    monkeypatch.setattr(cli, "urlopen", fail)
    with pytest.raises(RuntimeError, match="연결"):
        cli.ask(cli.make_payload("hello"), "private-token")

@pytest.mark.parametrize("body", [b"not json", b'{"status":"success","response":""}'])
def test_bad_response_is_rejected(monkeypatch, body):
    monkeypatch.setattr(cli, "urlopen", lambda *a, **k: io.BytesIO(body))
    with pytest.raises(RuntimeError):
        cli.ask(cli.make_payload("hello"), "private-token")

def test_success_sends_bearer_and_returns_answer(monkeypatch):
    seen={}
    def reply(req, **kwargs):
        seen["authorization"]=req.get_header("Authorization")
        seen["payload"]=json.loads(req.data)
        return io.BytesIO(b'{"status":"success","response":"42","memory_saved":true}')
    monkeypatch.setattr(cli, "urlopen", reply)
    assert cli.ask(cli.make_payload("17+25"), "private-token")["response"] == "42"
    assert seen["authorization"] == "Bearer private-token"
    assert seen["payload"]["query"] == "17+25"

@pytest.mark.parametrize("words", [["너는 누구니??"], ["너는", "누구니??"]])
def test_positional_query(words, capsys):
    """따옴표로 묶은 질문과 여러 단어 인자를 동일한 질문으로 전송한다."""
    assert cli.main([*words, "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["payload"]["query"] == "너는 누구니??"

def test_duplicate_query_forms_are_rejected():
    """위치 인자와 --query를 동시에 주면 질문 선택을 추측하지 않고 거부한다."""
    with pytest.raises(SystemExit) as error:
        cli.main(["first", "--query", "second", "--dry-run"])
    assert error.value.code == 2
