"""요청한 자동 수정 기능을 원본 백업과 해시 검증 후 설치하는 단일 작업용 실행기.

입력 JSON은 수정할 두 기존 파일과 config 추가 설정만 포함한다.
dry_run에서는 문법/원본 해시만 확인하고, apply 후 테스트 실패 시 원본을 복구한다.
"""
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
ALLOWED = {"FastAPI/LangGraph/sps_main_orchestrator.py",
           "FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_Network_Sniffer.py"}


def main():
    request = json.load(sys.stdin)
    originals, replacements = {}, {}
    if set(request["files"]) != ALLOWED:
        raise ValueError("수정 대상 불일치")
    for name, spec in request["files"].items():
        target = ROOT / name
        original = target.read_bytes()
        # source_read는 줄바꿈을 정규화하므로 동일한 규칙으로 비교한다.
        # 백업/복구에는 정규화하지 않은 원본 바이트를 그대로 사용한다.
        normalized = ("\n".join(original.decode("utf-8").splitlines()) + "\n").encode("utf-8")
        if hashlib.sha256(normalized).hexdigest() != spec["before_sha256"]:
            raise ValueError("원본이 변경됨: " + name)
        originals[name] = original
        replacements[name] = spec["content"].encode("utf-8")
    name = "config.py"
    originals[name] = (ROOT / name).read_bytes()
    if b"SPS_SOURCE_REPAIR_ALLOWED_PATHS" in originals[name]:
        raise ValueError("자동 수정 설정이 이미 존재함")
    replacements[name] = originals[name] + request["config_append"].encode("utf-8")
    for name, data in replacements.items():
        ast.parse(data.decode("utf-8"), filename=name)
    summary = {name: hashlib.sha256(data).hexdigest() for name, data in replacements.items()}
    if request.get("dry_run", True):
        print(json.dumps({"dry_run": True, "applicable": True, "after_sha256": summary}))
        return
    backups = {}
    stamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S")
    # 설치 전에 모든 원본을 백업한다. 기존 백업이 있으면 덮어쓰지 않고 중단한다.
    for name, data in originals.items():
        target = ROOT / name
        backup = target.with_name(target.stem + "_BACKUP_" + stamp + target.suffix)
        with backup.open("xb") as stream:
            stream.write(data)
        os.chmod(backup, target.stat().st_mode & 0o777)
        backups[name] = str(backup.relative_to(ROOT))
    def write(name, data):
        target = ROOT / name
        fd, temporary = tempfile.mkstemp(prefix=".sps_update_", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, target.stat().st_mode & 0o777)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    try:
        for name, data in originals.items():
            if (ROOT / name).read_bytes() != data:
                raise ValueError("설치 중 원본 변경 감지")
        for name, data in replacements.items():
            write(name, data)
        result = subprocess.run([sys.executable, str(ROOT / "haness/tests/test_source_repair.py")],
                                cwd=ROOT, capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError("설치 후 테스트 실패: " + result.stderr[-3000:])
        for name, digest in summary.items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError("설치 후 해시 불일치")
        print(json.dumps({"success": True, "backups": backups, "after_sha256": summary,
                          "tests": result.stderr[-3000:]}, ensure_ascii=False))
    except BaseException:
        for name, data in originals.items():
            write(name, data)
        raise


if __name__ == "__main__":
    main()
