"""config.py 패치 실패 원인 진단(읽기 전용): 줄끝(CRLF), 653행 원문 바이트, 파일 끝 개행 여부를 출력한다."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
data = (ROOT / "config.py").read_bytes()
lines = data.split(b"\n")
print(json.dumps({
    "crlf_count": data.count(b"\r\n"),
    "lf_count": data.count(b"\n"),
    "line_653_repr": repr(lines[652]),
    "line_652_repr": repr(lines[651]),
    "ends_with_newline": data.endswith(b"\n"),
    "total_lines": len(lines),
}, ensure_ascii=False))
