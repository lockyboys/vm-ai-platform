"""AIA 추가 전송 대상 32개를 검증 후 별도 폴더로 이동한다."""
import hashlib
import json
import stat
import sys
from pathlib import Path

ROOT = Path("/data/vm_project/outputs/insurance_docs/AIA/first_page_named")
LOG = Path("/data/vm_project/outputs/insurance_docs/AIA/first_page_titles")
TARGET = ROOT / "추가전송_32개"
NAMES = json.loads("[\"무배당  프라임평생설계보험.pdf\",\"무배당  프라임평생설계보험5.pdf\",\"무배당  프라임평생설계보험6.pdf\",\"무배당  프라임평생설계보험  약관.pdf\",\"무배당 시니어보장플랜5.pdf\",\"무배당 시니어보장플랜.pdf\",\"무배당 시니어보장플랜2.pdf\",\"무배당 시니어보장플랜3.pdf\",\"무배당 시니어보장플랜4.pdf\",\"무배당  AIG  프라임종신의료비보장보험( 건강관리형,   순수보장형).pdf\",\"무배당  AAA교통상해보험2.pdf\",\"무배당  AAA교통상해보험.pdf\",\"무배당  어린이의료비보장보험.pdf\",\"무배당  어린이의료비보장보험2.pdf\",\"무배당  어린이의료비보장보험3.pdf\",\"무배당  AIG상해보험.pdf\",\"무배당  AIG상해보험7.pdf\",\"무배당  AIG상해보험2.pdf\",\"무배당  AIG상해보험3.pdf\",\"무배당  AIG상해보험4.pdf\",\"무배당  AIG상해보험5.pdf\",\"무배당  AIG상해보험6.pdf\",\"무배당  AIG  다보장의료보험.pdf\",\"무배당  AIG YES  실버  종신보험.pdf\",\"무배당  AIG  마이웨이  종신보험.pdf\",\"무배당  AIG YES  실버  보험.pdf\",\"무배당  AIG YES  실버  보험2.pdf\",\"무배당  AIG  마이웨이  정기보험.pdf\",\"무배당  프라임평생설계보험7.pdf\",\"무배당  프라임평생설계보험4.pdf\",\"무배당 AIG대중교통상해보험.pdf\",\"무배당 AIG대중교통상해보험2.pdf\"]")

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    opts = json.loads(sys.stdin.read() or "{}")
    apply = opts.get("apply") is True
    if len(NAMES) != 32 or len(set(NAMES)) != 32:
        raise ValueError("대상 이름 중복 또는 개수 오류")
    records = []
    for log, field in (("copies.jsonl", "status"), ("recovery.jsonl", "copy_status")):
        with (LOG / log).open(encoding="utf-8") as stream:
            records += [r for line in stream if (r := json.loads(line)).get(field) == "COPY_VERIFIED"]
    expected_hashes = {r["sha256"] for r in records}
    pdfs = [p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    if len(pdfs) != 4663 or sum(p.stat().st_size for p in pdfs) != 6732795904:
        raise ValueError("서버 사본 수 또는 크기가 이전 대조 결과와 다름")
    if TARGET.exists():
        raise FileExistsError("전송 대상 폴더가 이미 있음")
    planned = []
    for name in NAMES:
        path = ROOT / name
        if path.name != name or not path.is_file() or path.is_symlink():
            raise ValueError("대상 파일이 없거나 일반 PDF가 아님")
        digest = sha(path)
        if digest not in expected_hashes:
            raise ValueError("검증 기록과 파일 내용 불일치: " + name)
        planned.append((path, path.stat().st_size, digest))
    total = sum(size for _, size, _ in planned)
    if total != 12963054:
        raise ValueError("32개 총 크기가 예상과 다름")
    if apply:
        TARGET.mkdir(mode=0o755)
        TARGET.chmod(0o755)
        moved = []
        try:
            for path, size, digest in planned:
                dest = TARGET / path.name
                previous_mode = stat.S_IMODE(path.stat().st_mode)
                path.rename(dest)
                moved.append((path, dest, previous_mode))
                dest.chmod(0o644)
            if len(list(TARGET.iterdir())) != 32 or sum(p.stat().st_size for p in TARGET.iterdir()) != total:
                raise ValueError("이동 후 건수 또는 크기 불일치")
            if any(sha(dest) != digest for (_, _, digest), (_, dest, _) in zip(planned, moved)):
                raise ValueError("이동 후 해시 불일치")
            if any(stat.S_IMODE(dest.stat().st_mode) != 0o644 for _, dest, _ in moved):
                raise ValueError("이동 후 읽기 권한 불일치")
        except Exception:
            for old, new, previous_mode in reversed(moved):
                if new.exists() and not old.exists():
                    new.rename(old)
                    old.chmod(previous_mode)
            raise
    print(json.dumps({"applied": apply, "directory": str(TARGET), "files": len(planned),
                      "bytes": total, "remaining_in_parent": len(pdfs) - len(planned),
                      "hashes_verified": len(planned)}, ensure_ascii=False))
if __name__ == "__main__":
    main()
