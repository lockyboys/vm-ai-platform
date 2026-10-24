"""중지한 서비스의 실행 모듈과 작업 경로만 읽는다. 환경 변수나 비밀정보는 조회하지 않는다."""
import json
import re
import subprocess
result = subprocess.run(
    ["systemctl", "show", "fastapi-insurance-rag.service",
     "--property=ExecStart,WorkingDirectory,FragmentPath"],
    capture_output=True, text=True, timeout=15, check=True,
)
values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
command = values.get("ExecStart", "")
modules = re.findall(r"(?<![\w/])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*):app\b", command)
sources = re.findall(r"(/[^\s;{}]+\.py)\b", command)
print(json.dumps({"unit_file":values.get("FragmentPath"), "working_directory":values.get("WorkingDirectory"),
                  "app_modules":modules, "python_sources":sources}, ensure_ascii=False))
