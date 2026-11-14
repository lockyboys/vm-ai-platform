"""추적 안 된 잔여 파일을 기능별로 묶어 커밋한다 (LuckyBoys 2026-11-14 승인: "전부 기능별 커밋").

동작
    1) git status --porcelain -uall 로 '??' 파일 목록을 읽는다(수정된 추적 파일이 있으면 중단).
    2) 경로 규칙으로 그룹을 나눈다(아래 PLAN). 어느 그룹에도 안 들어가는 파일이 있으면 중단(추측 금지).
    3) 표준입력이 'apply' 이면 그룹마다 git add -- <파일들> → git commit. 그 외에는 계획만 출력(dry-run).
안전장치
    - 시작 전 staged 파일이 있으면 중단(다른 작업을 섞지 않음).
    - 커밋마다 staged 목록이 그 그룹과 정확히 같은지 확인 후 커밋.
    - push 하지 않는다. 이 스크립트 자신은 마지막 그룹(scripts 20261114)에 들어간다.
"""
import collections
import re
import subprocess
import sys

TRAILER = ("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01PXp2JMsyEP1jQ3dMvwd7Wn")

# (커밋 메시지, 그룹 키 목록) — 순서대로 커밋
PLAN = [
    ("chore(scripts): one-off haness->harness migration and move-conflict scripts 2026-11-02", ["oneoff:20261102"]),
    ("chore(scripts): one-off review contract / persona sha / harness move commit scripts 2026-11-03", ["oneoff:20261103"]),
    ("chore(scripts): one-off selffix module/test move and provider comparison scripts 2026-11-10", ["oneoff:20261110"]),
    ("chore(scripts): one-off harness test listing and regression runner 2026-11-11", ["oneoff:20261111"]),
    ("test(selffix): add 100-case calculator/tetris self-fix benchmark 2026-11-10", ["tests:selffix_benchmark_100_20261110"]),
    ("feat(selffix-demo): combo20 gemini run2 engines and benches", ["combo20_run2", "tests:selffix_combo20"]),
    ("chore(scripts): insurer disclosure hero probe (py/js)", ["scripts:hero_probe"]),
    ("chore(backup): preserve originals from haness->harness migration 2026-11-02", ["backup:haness_to_harness_20261102"]),
    ("chore(backup): preserve 2026-10-25/26 backups (regression, payload rules, provider tuning, gemini agent)",
     ["backup:git_feature_commits_20261025_0500", "backup:payload_execution_flow_20261025",
      "backup:payload_sync_rule_20261025", "backup:pending_feature_commits_20261025_0520",
      "backup:provider_tuning_20261025", "backup:regression_20261025_032232", "backup:regression_cache_20261025",
      "backup:regression_round2_20261025", "backup:sps_gemini_agent_pre"]),
    ("chore(backup): preserve 2026-11-01~03 backups (gemini timeout, ollama auto select, heungkuk, review selffix/contract)",
     ["backup:gemini_timeout_runfile_20261101", "backup:ollama_auto_select_20261101", "backup:heungkuk_terms_20261102",
      "backup:review_selffix_20261102", "backup:review_contract_proposal_20261103"]),
    ("chore(memory): source review and proposal job records", ["memory:source_reviews", "memory:source_proposals"]),
    ("chore(memory): selffix benchmark records and reports", ["memory:selffix_bench"]),
    ("chore(memory): blind review and orchestrator job records",
     ["memory:blind_review_jobs", "memory:orchestrator_jobs", "memory:orchestrator_runs"]),
    ("docs(memory): checkpoint snapshots 2026-11-02/10/11", ["memory:checkpoints"]),
    ("chore(scripts): commit leftovers by feature script 2026-11-14", ["oneoff:20261114"]),
]


def git(*args: str) -> str:
    """git 명령을 실행하고 표준출력을 돌려준다. 실패하면 예외."""
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def group_of(path: str) -> str:
    """경로 → 그룹 키. 규칙에 없는 경로는 'other'(→ 중단 사유)."""
    if path.startswith("harness/backups/"):
        name = path.split("/")[2]
        return "backup:sps_gemini_agent_pre" if name.endswith(".py") else "backup:" + name
    if path.startswith("harness/memory/"):
        return "memory:" + path.split("/")[2]
    if path.startswith("harness/tests/"):
        return "tests:" + path.split("/")[2]
    if path.startswith("harness/scripts/insurer_disclosure_hero_probe"):
        return "scripts:hero_probe"
    if "/combo20/" in path:
        return "combo20_run2"
    if path.startswith("FastAPI/LangGraph/"):
        match = re.search(r"_(2026\d{4})", path)
        return "oneoff:" + match.group(1) if match else "other"
    return "other"


def main() -> int:
    apply = sys.stdin.read().strip() == "apply"
    lines = git("status", "--porcelain", "-uall").splitlines()
    tracked_changes = [line for line in lines if not line.startswith("??")]
    if tracked_changes:
        print("중단: 추적 파일 변경이 있음", tracked_changes[:10]); return 2
    if git("diff", "--cached", "--name-only").strip():
        print("중단: 이미 staged 된 파일이 있음"); return 2
    groups = collections.defaultdict(list)
    for line in lines:
        path = line[3:].strip().strip('"')
        groups[group_of(path)].append(path)
    planned = {key for _, keys in PLAN for key in keys}
    unknown = sorted(set(groups) - planned)
    if unknown:
        print("중단: 계획에 없는 그룹", {k: groups[k][:5] for k in unknown}); return 2
    total = 0
    for message, keys in PLAN:
        paths = [p for k in keys for p in groups.get(k, [])]
        if not paths:
            print(f"건너뜀(파일 없음): {message}"); continue
        total += len(paths)
        print(f"[{len(paths):>3}] {message}")
        if not apply:
            continue
        git("add", "--", *paths)
        staged = set(git("diff", "--cached", "--name-only").splitlines())
        if staged != set(paths):
            print("중단: staged 목록 불일치", sorted(staged ^ set(paths))[:10]); return 3
        git("commit", "-q", "-m", message, "-m", TRAILER)
        print("   →", git("log", "-1", "--format=%h").strip())
    print(f"합계 {total}개 파일, 모드={'apply' if apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
