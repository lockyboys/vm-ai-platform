"""스스로 고치는 앱(review_python_source) 개선분만 골라 한 번에 커밋한다 (2026-11-21, 일회용, LuckyBoys 승인
'그 세션 것까지 함께 커밋' = 자가 수정 앱의 상황별 대응표·반복 로직(다른 세션)까지 포함).

왜 스크립트인가:
- config.py에는 자가 수정 말고 다른 작업(공시 수집기 EVIDENCE_RULE_LOOP·PROFILE_AUTODISCOVER, SPS_WEB_SEARCH 온보딩,
  GPU IP)이 섞여 있고 그 세션이 지금도 고치고 있다 → config.py는 'HEAD + 자가 수정 블록'만으로 만든다.
- index에는 다른 세션이 스테이징한 파일이 있어 일반 git commit을 쓸 수 없다 → 임시 index로 커밋한다.
인자 없으면 dry-run(검사만), sys.argv[1] == "--apply"일 때만 커밋. push하지 않는다. 작업 트리는 바꾸지 않는다.
"""
import difflib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLY = len(sys.argv) > 1 and sys.argv[1] == "--apply"
# 작업 트리 내용 그대로 넣을 파일(전부 자가 수정 앱 것)
WHOLE_FILES = [
    "harness/mcp/tools/multi_persona_tools.py",
    "harness/mcp/tools/auto_apply.py",
    "common/common_function.py",
    "harness/tests/test_selffix_stop_reason.py",
    "harness/tests/test_selffix_focus_salvage_timeout.py",
    "harness/tests/test_selffix_ollama_preflight.py",
    "harness/tests/test_selffix_action_table.py",
    "harness/tests/test_review_feedback_rounds.py",
    "harness/tests/test_selffix_contract_retry.py",
    "harness/tests/test_provider_fatal_stop.py",
    "harness/tests/test_review_auto_apply_20261110.py",
    "FastAPI/LangGraph/backup_config_selffix_20261121.py",
    "FastAPI/LangGraph/backup_config_preflight_20261121.py",
    "FastAPI/LangGraph/commit_selffix_part_20261121.py",
    "FastAPI/LangGraph/run_commit_selffix_part_20261121.py",
]
# config.py에서 자가 수정 블록: (HEAD에 있는 기준 줄, 작업 트리에서 그 기준 줄 대신/뒤에 들어간 블록의 시작·끝 표시)
MY_WORDS = ("MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS", "FEEDBACK_CONTEXT_LINES", "REVERT_MAX_FUNCTIONS",
            "PROVIDER_TIMEOUT_MAX_SECONDS", "MULTI_PERSONA_SELFFIX_", "job_timeout_seconds",
            "try pulling it first", "MULTI_PERSONA_OLLAMA_REJECT_URLS", "OLLAMA_PREFLIGHT_TIMEOUT")
MESSAGE = ("feat(selffix): focus failing tests, function-level revert, provider job timeout, stop_reason, "
           "situation action table loop, Ollama preflight\n\n"
           "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01PXp2JKBTsb3CZKbbPSQjrV\n")


def git(*args, data=None, env=None):
    """git 실행. 실패하면 예외(반쯤 된 상태를 남기지 않음)."""
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, input=data, check=False,
                          env={**os.environ, **(env or {})})
    if done.returncode != 0:
        raise RuntimeError(f"git {args[0]} 실패: {done.stderr.decode(errors='replace')[:400]}")
    return done.stdout.decode("utf-8")


def block(text, start_marker, end_marker):
    """text에서 start_marker 줄부터 end_marker 줄까지(포함)를 잘라 낸다. 각 표시는 정확히 1번 있어야 함."""
    lines = text.splitlines(keepends=True)
    s = [i for i, l in enumerate(lines) if start_marker in l]
    e = [i for i, l in enumerate(lines) if end_marker in l]
    if len(s) != 1 or len(e) != 1 or e[0] < s[0]:
        raise RuntimeError(f"블록 표시를 찾지 못함: {start_marker!r} ~ {end_marker!r}")
    return "".join(lines[s[0]:e[0] + 1])


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f"HEAD에서 기준 줄을 1번 찾지 못함: {old[:60]!r}")
    return text.replace(old, new, 1)


def build_config():
    """HEAD의 config.py에 자가 수정 블록 4곳만 넣는다."""
    head = git("show", "HEAD:config.py")
    cur = (ROOT / "config.py").read_text(encoding="utf-8")
    # ① 최대 라운드 3 → 10 (주석 포함)
    b1 = block(cur, "2026-11-21 (LuckyBoys 요청 '고쳐질 때까지 반복')", "MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS = ")
    staged = replace_once(head, "MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS = 3\n", b1)
    # ② 피드백 코드 줄·되돌림·공급자 한도 상한·상황별 대응표·제자리걸음
    anchor = "MULTI_PERSONA_AUTO_APPLY_FEEDBACK_MAX_FAILURES = 40\n"
    b2 = block(cur, "2026-11-21 (LuckyBoys 승인 '실패 테스트 집중')", "MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS = ")
    staged = replace_once(staged, anchor, anchor + b2)
    # ③ ollama 공급자 작업 한도 3시간
    old_ollama = '    "ollama": {"cli": "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py", "llm": "ollama"},\n'
    b3 = block(cur, "2026-11-21 (LuckyBoys 승인: ollama 3시간)", '"job_timeout_seconds": 10800},')
    staged = replace_once(staged, old_ollama, b3)
    # ④ 404 치명 오류 + Ollama 사전 점검 설정
    a4 = '    "(status code: 500)": "Ollama 서버 오류(500)",\n'
    b4 = block(cur, "2026-11-21 (LuckyBoys 선택 1안): 설정한 모델이", '"try pulling it first"')
    staged = replace_once(staged, a4, a4 + b4)
    a5 = "MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE = 3\n"
    b5 = block(cur, "2026-11-21 (LuckyBoys 선택 1안): 스스로 고치는 앱이 Ollama", "MULTI_PERSONA_OLLAMA_PREFLIGHT_TIMEOUT_SECONDS")
    staged = replace_once(staged, a5, a5 + b5)
    compile(staged, "config.py", "exec")
    # 검사: 커밋 내용과 작업 트리의 남는 차이(다른 작업 몫)에 자가 수정 줄이 없어야 하고, 빠진 줄도 없어야 한다
    diff = [l for l in difflib.unified_diff(staged.splitlines(), cur.splitlines(), lineterm="", n=0)
            if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    removed = [l for l in diff if l.startswith("-") and "SPS_GPU_SSH_HOST" not in l]  # GPU IP 줄은 다른 작업이 바꿈
    mine_left = [l for l in diff if any(w in l for w in MY_WORDS)]
    print(f"[검사] config.py 남는 차이(다른 작업 몫) {len(diff)}줄, 자가 수정 줄 남음 {len(mine_left)}, 예상 밖 삭제 {len(removed)}")
    if mine_left or removed:
        raise RuntimeError("남는 차이가 예상과 다름:\n" + "\n".join((mine_left + removed)[:20]))
    return staged


def main():
    staged = build_config()
    for path in WHOLE_FILES:
        text = (ROOT / path).read_text(encoding="utf-8")
        compile(text, path, "exec")
    print(f"[검사] 통째로 넣을 파일 {len(WHOLE_FILES)}개 문법 통과")
    if not APPLY:
        print("[dry-run] 커밋하지 않았습니다.")
        return 0
    old_head = git("rev-parse", "HEAD").strip()
    blobs = {"config.py": git("hash-object", "-w", "--stdin", data=staged.encode("utf-8")).strip()}
    for path in WHOLE_FILES:
        blobs[path] = git("hash-object", "-w", "--", path).strip()
    with tempfile.TemporaryDirectory() as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git("read-tree", "HEAD", env=env)
        for path, blob in blobs.items():
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git("write-tree", env=env).strip()
    new = git("commit-tree", tree, "-p", old_head, data=MESSAGE.encode("utf-8")).strip()
    git("update-ref", "-m", "commit: selffix improvements", "HEAD", new, old_head)
    for path, blob in blobs.items():           # 진짜 index도 이 항목들만 새 HEAD와 맞춘다
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}")
    print(git("show", "--stat", "--format=%h %s", "HEAD"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
