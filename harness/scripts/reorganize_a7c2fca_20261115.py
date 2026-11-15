"""push된 기록 재정리: a7c2fca에 섞인 402 정지 변경을 402 커밋(e5bf2d6)으로 옮긴다 (2026-11-15, LuckyBoys 결정).

LuckyBoys 결정: "강제 push를 감수하고 다시 정리", "a7c2fca만 나눠 재정리".
방법(작업 트리·스테이징은 건드리지 않음 — git 내부 명령으로 커밋만 새로 만든다)
1. 13fe27d 다음 커밋부터 HEAD까지 23개를 오래된 순으로 다시 만든다(메시지·작성자·날짜 그대로).
2. a7c2fca와 그 뒤 e5bf2d6 전까지(8d97181, e50f5a3, 41d5b44)는 multi_persona_tools.py를
   "292f0c3 판 + runtime_cap 변경만" 판으로 바꾼다. 402 변경은 e5bf2d6에서 들어가게 된다.
3. 마지막 커밋의 파일 내용(tree)이 지금 HEAD와 완전히 같아야만 진행한다(내용 손실 없음 증명).
4. --apply일 때만: 옛 HEAD를 refs/harness-backup/reorganize-<시각>에 남기고 브랜치를 새 HEAD로 옮긴다.
   push는 하지 않는다. 강제 push 명령은 출력만 하고 LuckyBoys가 직접 실행한다.
"""
import difflib
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLY = len(sys.argv) > 1 and sys.argv[1] == "--apply"
BASE = "13fe27d1ee76e6ac887ad1741b32749961e02cd2"
BEFORE_MIXED = "292f0c3ea8bae08dd6f2faae06433f89933bc2a1"   # a7c2fca 바로 앞 커밋
MIXED = "a7c2fca37d82f60deb86c97e656e4889fbb22093"
FATAL_COMMIT = "e5bf2d6b6915eace85dc3f42bf43917ab9867a3a"
PATH = "harness/mcp/tools/multi_persona_tools.py"
EXPECTED_HEAD = "dffd6c4d480c6a887f4e95496ae3c39906c5b303"

# runtime_cap 변경(a7c2fca의 첫 번째 변경 묶음)만 292f0c3 판에 넣기 위한 정확한 치환 2개
RC_REPLACEMENTS = [
    ("def _systemd_command(arguments: list[str], timeout: int, purpose: str) -> tuple[str, list[str]]:\n",
     "def _systemd_command(arguments: list[str], timeout: int, purpose: str,\n"
     "                     runtime_cap: int | None = None) -> tuple[str, list[str]]:\n"),
    ("    runtime_max = min(int(timeout), int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS))\n",
     "    # 2026-11-14 LuckyBoys 선택 A: 자기 수리(self_repair_run)만 config.SELF_REPAIR['job_timeout_seconds']\n"
     "    # (36,000초)를 runtime_cap 으로 넘겨 상한을 올린다. runtime_cap=None(기본)이면 기존 동작 그대로.\n"
     "    # 잘못된 runtime_cap(양의 정수 아님, bool 포함)은 명령을 만들기 전에 거부한다.\n"
     "    if runtime_cap is not None and (isinstance(runtime_cap, bool) or not isinstance(runtime_cap, int)\n"
     "                                    or runtime_cap < 1):\n"
     "        raise ValueError(\"runtime_cap must be a positive integer\")\n"
     "    cap = int(project_config.SPS_GENERAL_UNIT_RUNTIME_SECONDS) if runtime_cap is None else runtime_cap\n"
     "    runtime_max = min(int(timeout), cap)\n"),
]


def git(*args: str, env: dict | None = None, data: bytes | None = None) -> str:
    """git 실행(실패하면 예외). 출력 앞뒤 공백은 지운다."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, input=data,
                          env={**os.environ, **(env or {})}, check=False)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {done.stderr.decode(errors='replace')[:500]}")
    return done.stdout.decode("utf-8", errors="replace").strip()


def changed_lines(old: str, new: str) -> list[str]:
    """old → new 에서 더하거나 뺀 줄 목록(비교용)."""
    return [line for line in difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))]


def main() -> int:
    head = git("rev-parse", "HEAD")
    branch = git("symbolic-ref", "--short", "HEAD")
    if head != EXPECTED_HEAD:
        print(f"[중단] HEAD가 조사 때와 다름: {head}")
        return 1
    if git("diff", "--cached", "--name-only"):
        print("[중단] 스테이징된 파일이 있음(먼저 비워야 함)")
        return 1

    # 1) runtime_cap만 들어간 판 만들기 + 검증
    base_text = git("show", f"{BEFORE_MIXED}:{PATH}") + "\n"
    mixed_text = git("show", f"{MIXED}:{PATH}") + "\n"
    rc_text = base_text
    for old, new in RC_REPLACEMENTS:
        if rc_text.count(old) != 1:
            print(f"[중단] 치환 대상이 1번이 아님: {old[:60]!r}")
            return 1
        rc_text = rc_text.replace(old, new)
    compile(rc_text, PATH, "exec")
    to_rc = changed_lines(base_text, rc_text)
    rc_to_mixed = changed_lines(rc_text, mixed_text)
    if any("provider_fatal" in line for line in to_rc) or any("runtime_cap" in line for line in rc_to_mixed):
        print("[중단] runtime_cap 판에 402 변경이 섞였거나, 402 변경에 runtime_cap이 남음")
        return 1
    if not all("runtime_cap" in "\n".join(to_rc) for _ in [0]) or not rc_to_mixed:
        print("[중단] 나눈 결과가 비어 있음")
        return 1
    rc_blob = git("hash-object", "-w", "--stdin", data=rc_text.encode("utf-8"))
    mixed_blob = git("rev-parse", f"{MIXED}:{PATH}")

    # 2) 커밋을 오래된 순으로 다시 만든다
    commits = git("rev-list", "--reverse", f"{BASE}..{head}").split()
    replace_until = commits.index(FATAL_COMMIT)        # 이 앞(a7c2fca~41d5b44)까지 rc 판으로 바꾼다
    start = commits.index(MIXED)
    parent, rows = BASE, []
    with tempfile.TemporaryDirectory() as tmp:
        index_env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        for i, sha in enumerate(commits):
            tree = git("rev-parse", f"{sha}^{{tree}}")
            changed = start <= i < replace_until
            if changed:
                if git("rev-parse", f"{sha}:{PATH}") != mixed_blob:
                    print(f"[중단] {sha[:7]}의 {PATH}가 a7c2fca 판과 다름")
                    return 1
                git("read-tree", tree, env=index_env)
                git("update-index", "--cacheinfo", f"100644,{rc_blob},{PATH}", env=index_env)
                tree = git("write-tree", env=index_env)
            meta = git("log", "-1", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI", sha).split("\x00")
            env = dict(zip(("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
                            "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE"), meta))
            message = git("log", "-1", "--format=%B", sha) + "\n"
            new_sha = git("commit-tree", tree, "-p", parent, "-F", "-", env=env, data=message.encode("utf-8"))
            rows.append((sha[:7], new_sha[:7], "바뀜(402 부분 뺌)" if changed else "", message.splitlines()[0][:60]))
            parent = new_sha
    new_head = parent

    # 3) 최종 내용이 지금과 같은지
    same = git("rev-parse", f"{new_head}^{{tree}}") == git("rev-parse", f"{head}^{{tree}}")
    print(f"브랜치={branch} 옛 HEAD={head[:7]} 새 HEAD={new_head[:7]} 최종 내용 동일={same}")
    print(f"runtime_cap 판에서 a7c2fca 판까지 차이(=402 커밋으로 옮겨질 줄) {len(rc_to_mixed)}줄")
    for row in rows:
        print(" | ".join(row))
    if not same:
        print("[중단] 최종 내용이 다름 — 반영하지 않음")
        return 1
    if not APPLY:
        print("[dry-run] 새 커밋 개체만 만들었고 브랜치는 그대로입니다.")
        return 0
    backup = f"refs/harness-backup/reorganize-{datetime.now():%Y%m%d-%H%M%S}"
    git("update-ref", backup, head)
    git("update-ref", f"refs/heads/{branch}", new_head, head)
    print(f"[반영] {branch}: {head[:7]} → {new_head[:7]} (옛 HEAD 백업 {backup})")
    print(f"강제 push 명령(LuckyBoys가 직접): git push --force-with-lease={branch}:{head} origin {branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
