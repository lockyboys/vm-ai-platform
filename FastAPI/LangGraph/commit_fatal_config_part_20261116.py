"""config.py의 '즉시 정지 패턴' 4줄 블록 + 테스트만 골라 커밋한다 (2026-11-16, 일회용, LuckyBoys 커밋 승인).

왜 스크립트인가:
- config.py 작업 트리에는 다른 세션의 변경(onboard_excluded_hosts, start_link_*)이 같이 있다.
- git_commit 도구의 keep_other_staged 는 작업 트리 내용을 통째로 커밋하므로 남의 변경까지 들어간다.
- index 에는 다른 세션이 스테이징해 둔 파일 2개가 있어 일반 `git commit` 도 쓸 수 없다.
그래서 '임시 index'(GIT_INDEX_FILE)에서 HEAD + 제 블록만으로 트리를 만들어 커밋하고,
진짜 index 는 이 두 파일 항목만 새 HEAD 와 같게 맞춘다(다른 세션의 스테이징은 그대로 유지).

동작: 인자 없으면 dry-run(검사만), sys.argv[1] == "--apply" 일 때만 커밋. push 는 하지 않는다.
"""
import difflib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # /data/vm_project
APPLY = len(sys.argv) > 1 and sys.argv[1] == "--apply"
ANCHOR = '    "error code: 401": "LLM API 키 오류(401)",'   # 블록을 넣을 바로 앞 줄(HEAD 에 있음)
MY_WORDS = ("credit balance is too low", "out of memory", "out-of-memory", "(status code: 500)")
TEST_PATH = "harness/tests/test_provider_fatal_stop.py"
MESSAGE = ("fix(selffix): stop immediately on Anthropic credit-too-low and Ollama OOM/500 errors\n\n"
           "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01PXp2JKBTsb3CZKbbPSQjrV\n")


def git(*args: str, data: bytes | None = None, env: dict | None = None) -> str:
    """git 실행. 실패하면 예외로 멈춘다(반쯤 된 상태를 남기지 않기 위해)."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, input=data, check=False,
                          env={**os.environ, **(env or {})})
    if done.returncode != 0:
        raise RuntimeError(f"git {args[0]} 실패: {done.stderr.decode(errors='replace')[:400]}")
    return done.stdout.decode("utf-8")


def build_config() -> str:
    """HEAD 의 config.py 에 작업 트리의 '제 블록'만 끼워 넣은 내용을 만든다."""
    head_lines = git("show", "HEAD:config.py").splitlines(keepends=True)
    cur_lines = (ROOT / "config.py").read_text(encoding="utf-8").splitlines(keepends=True)
    h = [i for i, l in enumerate(head_lines) if l.rstrip("\n") == ANCHOR]
    c = [i for i, l in enumerate(cur_lines) if l.rstrip("\n") == ANCHOR]
    if len(h) != 1 or len(c) != 1:
        raise RuntimeError("기준 줄(error code: 401)을 HEAD/작업 트리에서 정확히 1번 찾지 못함")
    if head_lines[h[0] + 1].rstrip("\n") != "}":
        raise RuntimeError("HEAD 에서 기준 줄 다음이 '}' 가 아님 → 이미 블록이 커밋됐을 수 있음")
    # 작업 트리에서 기준 줄 다음부터 닫는 '}' 직전까지가 제 블록
    end = next(i for i in range(c[0] + 1, len(cur_lines)) if cur_lines[i].rstrip("\n") == "}")
    block = cur_lines[c[0] + 1:end]
    joined = "".join(block)
    if not all(w in joined for w in MY_WORDS):
        raise RuntimeError("블록에 기대한 4개 패턴이 모두 있지 않음")
    staged = "".join(head_lines[:h[0] + 1] + block + head_lines[h[0] + 1:])
    compile(staged, "config.py", "exec")            # 문법 검사
    # 검사: 커밋할 내용과 작업 트리의 차이 = 다른 세션 몫(추가 줄만), 거기에 제 패턴이 없어야 함
    diff = [l for l in difflib.unified_diff(staged.splitlines(), "".join(cur_lines).splitlines(), lineterm="", n=0)
            if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    removed = [l for l in diff if l.startswith("-")]
    leftover_mine = [l for l in diff if any(w in l for w in MY_WORDS)]
    print(f"[검사] 제 블록 {len(block)}줄 / 남는 차이(다른 세션 몫) 추가 {len(diff) - len(removed)}줄, 빠짐 {len(removed)}줄")
    if removed or leftover_mine:
        raise RuntimeError("남는 차이가 예상과 다름:\n" + "\n".join(diff[:20]))
    return staged


def main() -> int:
    staged = build_config()
    test_text = (ROOT / TEST_PATH).read_text(encoding="utf-8")
    compile(test_text, TEST_PATH, "exec")
    if not APPLY:
        print("[dry-run] 커밋하지 않았습니다. 커밋 대상: config.py(블록만), " + TEST_PATH)
        return 0
    old_head = git("rev-parse", "HEAD").strip()
    cfg_blob = git("hash-object", "-w", "--stdin", data=staged.encode("utf-8")).strip()
    test_blob = git("hash-object", "-w", "--", TEST_PATH).strip()
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git("read-tree", "HEAD", env=env)                          # 임시 index = HEAD
        git("update-index", "--cacheinfo", f"100644,{cfg_blob},config.py", env=env)
        git("update-index", "--cacheinfo", f"100644,{test_blob},{TEST_PATH}", env=env)
        tree = git("write-tree", env=env).strip()
    new = git("commit-tree", tree, "-p", old_head, data=MESSAGE.encode("utf-8")).strip()
    git("update-ref", "-m", "commit: fatal provider patterns", "HEAD", new, old_head)  # HEAD 가 그새 바뀌었으면 실패
    # 진짜 index: 이 두 항목만 새 HEAD 와 같게(다른 세션의 스테이징 2개는 건드리지 않음)
    git("update-index", "--cacheinfo", f"100644,{cfg_blob},config.py")
    git("update-index", "--cacheinfo", f"100644,{test_blob},{TEST_PATH}")
    print(f"[반영] 커밋 {new[:7]} (부모 {old_head[:7]})")
    print(git("show", "--stat", "--format=%h %s", "HEAD"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
