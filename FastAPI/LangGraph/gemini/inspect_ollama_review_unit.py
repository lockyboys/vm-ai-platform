import subprocess, json
unit="sps-ollama-to-gemini-4bf7f4ed3721492dab6c50d45ffa7b8f"
for args in [["systemctl","show",unit,"--property=LoadState,ActiveState,Result,ExecMainStatus"],
             ["journalctl","-u",unit,"--no-pager","-n","20","-o","cat"]]:
 p=subprocess.run(args,capture_output=True,text=True,timeout=10)
 print(json.dumps({"command":args[0],"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr},ensure_ascii=False))
