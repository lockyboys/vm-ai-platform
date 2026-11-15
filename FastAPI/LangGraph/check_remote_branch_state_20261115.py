"""강제 push가 "stale info"로 거부된 원인 확인 (2026-11-15). 읽기 전용: ls-remote / rev-parse / merge-base / log 만 쓴다.

- remote_actual: 원격 서버에 지금 있는 feature/spds-v0.1 해시(git ls-remote, 네트워크 읽기)
- tracking_ref : 로컬이 알고 있는 origin/feature/spds-v0.1 해시
- 원격 해시가 로컬에 있으면, 예전 HEAD(dffd6c4)와의 관계와 원격에만 있는 커밋 목록을 보여 준다.
fetch는 하지 않는다(로컬 ref를 바꾸지 않음). 원격 해시가 로컬에 없으면 그 사실만 보고한다.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "feature/spds-v0.1"
OLD_HEAD = "dffd6c4d480c6a887f4e95496ae3c39906c5b303"


def git(*args: str) -> tuple[int, str]:
    """git 실행, (종료 코드, 출력) 반환."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=60)
    return done.returncode, (done.stdout or done.stderr).strip()


rc, remote_line = git("ls-remote", "origin", f"refs/heads/{BRANCH}")
remote_actual = remote_line.split()[0] if rc == 0 and remote_line else None
_, tracking = git("rev-parse", f"refs/remotes/origin/{BRANCH}")
report = {"remote_actual": remote_actual, "tracking_ref": tracking, "ls_remote_rc": rc,
          "ls_remote_error": None if rc == 0 else remote_line[:300]}
if remote_actual:
    known = git("cat-file", "-e", f"{remote_actual}^{{commit}}")[0] == 0
    report["remote_commit_known_locally"] = known
    if known:
        report["remote_is_ancestor_of_old_head"] = git("merge-base", "--is-ancestor", remote_actual, OLD_HEAD)[0] == 0
        report["old_head_is_ancestor_of_remote"] = git("merge-base", "--is-ancestor", OLD_HEAD, remote_actual)[0] == 0
        report["commits_only_on_remote"] = git("log", "--format=%h %an %ad %s", "--date=iso",
                                                f"{OLD_HEAD}..{remote_actual}")[1].splitlines()[:30]
print(json.dumps(report, ensure_ascii=False, indent=1))
