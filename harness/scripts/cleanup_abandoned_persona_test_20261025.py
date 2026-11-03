"""Remove only this session's exact, untracked abandoned test; preserve evidence."""
import hashlib,json,subprocess,sys
from pathlib import Path
def main():
    root=Path("/data/vm_project")
    relative="tests/harness/mcp/test_multi_persona_source_agent.py"
    path=root/relative
    request=json.loads(sys.stdin.read() or "{}")
    if not path.exists():
        print(json.dumps({"already_absent":True}));return
    expected="cd71b23d8be827062e70cd1c10da6a8f1c4558a41d301a41ad1ef4ea5e540cc9"
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise RuntimeError("Changed content; cleanup refused")
    tracked=subprocess.run(["git","ls-files","--error-unmatch",relative],cwd=root,capture_output=True)
    if tracked.returncode==0:raise RuntimeError("Tracked file; cleanup refused")
    evidence=root/"harness/memory/multi_persona_fixed_sequence_abandoned_20261025.md"
    if not evidence.is_file():raise RuntimeError("Missing preserved evidence")
    apply=request.get("apply",False) is True
    if apply:path.unlink()
    print(json.dumps({"apply":apply,"exact_untracked_file":True,"removed":not path.exists()}))
if __name__=="__main__":main()
