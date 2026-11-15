"""다시 정리할 커밋(13fe27d 이후 ~ HEAD)을 읽기 전용으로 조사한다 (2026-11-15, LuckyBoys 요청: 강제 push 감수하고 재정리).

출력(파일 하나): harness/memory/reorganize_commits_20261115.json
- commits: 오래된 순 [{sha, subject, files:[{status, path}]}]
- mixed_file_diffs: 기능이 섞였다고 본 커밋 a7c2fca의 multi_persona_tools.py 변경 diff
- 파일이 여러 커밋에 걸쳐 바뀌었는지(overlaps), 지금 작업 트리에서 커밋 안 된 변경이 있는 파일(dirty)
git 읽기 명령만 쓴다(log/show/diff/status). 아무것도 바꾸지 않는다.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# common_function을 import하면(이제 sudo 함수가 들어 있어) 실행 도구가 sudo 승인을 요구한다.
# 이 스크립트는 sudo를 쓰지 않는 읽기 전용이라 JSON 저장은 표준 라이브러리로만 한다.
_ = sys

BASE = "13fe27d1ee76e6ac887ad1741b32749961e02cd2"
MIXED = "a7c2fca37d82f60deb86c97e656e4889fbb22093"
OUT = ROOT / "harness/memory/reorganize_commits_20261115.json"


def git(*args: str) -> str:
    """git 읽기 명령 실행(실패하면 예외)."""
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def main() -> None:
    shas = git("rev-list", "--reverse", f"{BASE}..HEAD").split()
    commits, touched = [], {}
    for sha in shas:
        subject = git("log", "-1", "--format=%s", sha).strip()
        rows = [line.split("\t") for line in git("show", "--name-status", "--format=", sha).splitlines() if line]
        files = [{"status": r[0][:1], "path": r[-1]} for r in rows]
        for f in files:
            touched.setdefault(f["path"], []).append(sha[:7])
        commits.append({"sha": sha, "short": sha[:7], "subject": subject, "file_count": len(files), "files": files})
    dirty = [line[3:] for line in git("status", "--porcelain").splitlines() if line[:2].strip() and not line.startswith("??")]
    report = {
        "base": BASE,
        "head": git("rev-parse", "HEAD").strip(),
        "commit_count": len(commits),
        "commits": commits,
        "overlaps": {path: c for path, c in touched.items() if len(c) > 1},
        "dirty_tracked_now": dirty,
        "dirty_and_in_range": sorted(p for p in dirty if p in touched),
        "mixed_file_diffs": {
            "a7c2fca:harness/mcp/tools/multi_persona_tools.py":
                git("show", "--format=", MIXED, "--", "harness/mcp/tools/multi_persona_tools.py")[:60000],
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {k: report[k] for k in ("base", "head", "commit_count", "overlaps", "dirty_tracked_now", "dirty_and_in_range")}
    summary["commits"] = [(c["short"], c["file_count"], c["subject"][:70]) for c in commits]
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
