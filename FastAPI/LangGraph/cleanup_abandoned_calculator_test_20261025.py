"""Remove only this session's abandoned, unchanged calculator acceptance file."""
import hashlib,json,subprocess
from pathlib import Path
def main():
    p=Path("tests/harness/test_scientific_calculator_acceptance.py")
    result={"exists":p.exists(),"removed":False}
    if p.exists():
        tracked=subprocess.run(["git","ls-files","--error-unmatch",str(p)],capture_output=True).returncode==0
        if tracked or hashlib.sha256(p.read_bytes()).hexdigest()!="5a87b0656fe5a6cf5949979e03bd426bce7aa808a6aeaf460ef4803e93fddfe5":
            raise RuntimeError("Refuse to delete a changed or tracked file")
        p.unlink()
        result["removed"]=True
    print(json.dumps(result))
if __name__=="__main__":
    main()
