"""競合プロセスの実行元と認証キーの一致だけを確認し、秘密値は表示しない。"""
import json, re, subprocess
from pathlib import Path
from dotenv import dotenv_values
expected=dotenv_values("/etc/sps-harness/secrets.env").get("SPS_AUTH_JWT_SECRET_KEY")
ss=subprocess.run(["ss","-H","-ltnp","sport","=",":8003"],capture_output=True,text=True,timeout=10,check=True).stdout
for pid in re.findall(r"pid=(\d+)",ss):
    base=Path("/proc",pid)
    args=base.joinpath("cmdline").read_bytes().decode().split("\0")
    env=dict(x.split("=",1) for x in base.joinpath("environ").read_bytes().decode().split("\0") if "=" in x)
    modules=[a for a in args if re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:app",a)]
    print(json.dumps({"pid":pid,"executable":str(base.joinpath("exe").resolve()),"cwd":str(base.joinpath("cwd").resolve()),
                      "app_modules":modules,"python_scripts":[a for a in args if a.endswith(".py")],
                      "key_present":bool(env.get("SPS_AUTH_JWT_SECRET_KEY")),
                      "key_matches_protected":env.get("SPS_AUTH_JWT_SECRET_KEY")==expected,
                      "stdout_destination":str(base.joinpath("fd/1").resolve())}))
unit=Path("/etc/systemd/system/fastapi-insurance-rag.service").read_text()
print(json.dumps({"unit_environment_names":re.findall(r'^Environment=["\']?([A-Za-z_]\w*)=',unit,re.M),
                  "unit_environment_files":re.findall(r"^EnvironmentFile=(.*)$",unit,re.M)}))
