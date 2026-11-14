"""승인된 시간 정책 파일의 줄바꿈과 해시를 읽기 전용으로 확인한다."""
import json, hashlib
from pathlib import Path
paths=["config.py","harness/mcp/tools/execution_tools.py","haness/mcp/tools/multi_persona_tools.py","haness/mcp/tools/ssh_execution_tools.py","tests/harness/mcp/test_execution_tools.py","tests/harness/mcp/test_multi_persona_review_tool.py"]
print(json.dumps([{ "path":p,"sha256":hashlib.sha256(Path(p).read_bytes()).hexdigest(),"crlf":Path(p).read_bytes().count(b"\r\n"),"lf":Path(p).read_bytes().count(b"\n")} for p in paths]))
