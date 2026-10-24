from pathlib import Path

UNIT = Path(__file__).parents[1] / "systemd" / "sps-multi-persona.service"


def test_multi_persona_unit_uses_systemd_secret_injection():
    text = UNIT.read_text(encoding="utf-8")
    assert "Type=oneshot" in text
    assert "EnvironmentFile=/data/vm_project/.env" in text
    assert "EnvironmentFile=/etc/sps-harness/secrets.env" in text
    assert "ExecStart=/data/vm_project/venv/bin/python /data/vm_project/FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py" in text
    assert "--source-path /data/vm_project/FastAPI/LangGraph/agent_memory.py" in text
    assert "/etc/sps-harness/secrets.env" not in text.split("ExecStart=", 1)[1]
