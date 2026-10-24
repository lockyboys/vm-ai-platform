"""회귀 검증 후 기존 부분 스테이징 코어 호출과 이번 테스트 잔재 정리만 수행한다."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.database import CommonDatabase
from common.common_function import normalize_required_text
from harness.mcp.tools.git_mutation_tools import git_apply_cached_patch

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
request = json.load(sys.stdin)
# MCP의 argv는 SSH 전용이므로 로컬 검증 작업의 실행 플래그는 입력 JSON에서도 받는다.
args.apply = request.get("apply", args.apply) is True
operation = normalize_required_text(request.get("operation"), "operation")
if operation == "stage":
    result = git_apply_cached_patch(request["patch_text"], request["expected_paths"], dry_run=not args.apply)
    result.pop("staged_diff", None)  # 응답은 증빙 해시와 경로만 표시한다.
elif operation == "cleanup_test_record":
    subject = request["subject_id"]
    document_id = request["document_id"]
    if not re.fullmatch(r"memory-verification-[0-9a-f]{32}", subject):
        raise ValueError("only the synthetic memory test identity may be cleaned")
    if not re.fullmatch(r"[0-9a-f]{64}", document_id):
        raise ValueError("expected the synthetic memory document digest")
    selector = {"_id": document_id, "subject_id": subject, "created_by": subject,
                "thread_id": "old", "request_id": "persist"}
    database = CommonDatabase(database_role="STORY", connect_mariadb=False, connect_mongodb=True)
    try:
        row = database.find_one("agent_long_term_memory", selector)
        result = {"matched_count": int(row is not None), "dry_run": not args.apply}
        if args.apply and row is not None:
            deletion = database.delete_one("agent_long_term_memory", selector)
            result["deleted_count"] = deletion.deleted_count
            assert database.find_one("agent_long_term_memory", selector) is None
    finally:
        database.close()
else:
    raise ValueError("unsupported verification operation")
print(json.dumps(result, ensure_ascii=False))
