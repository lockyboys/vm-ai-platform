"""요청한 Git push의 원격/브랜치 확인 및 실행. stage와 commit은 별도 MCP 도구가 처리한다."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
def git(*args, timeout=30):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
        timeout=timeout, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
def clean(text):
    text = re.sub(r"(https?://)[^/@\s]+@", r"\1[redacted]@", text)
    for key, value in os.environ.items():
        if len(value) >= 8 and any(word in key.upper() for word in ("TOKEN","SECRET","PASSWORD","API_KEY")):
            text = text.replace(value, "[redacted]")
    return text[:2500]
def main():
    request = json.load(sys.stdin)
    branch_result = git("symbolic-ref", "--quiet", "--short", "HEAD")
    if branch_result.returncode:
        raise ValueError("Detached HEAD")
    branch = branch_result.stdout.strip()
    remote = git("config", "--get", "branch." + branch + ".remote").stdout.strip() or "origin"
    merge = git("config", "--get", "branch." + branch + ".merge").stdout.strip() or "refs/heads/" + branch
    if not merge.startswith("refs/heads/") or remote == ".":
        raise ValueError("원격 브랜치 확인 필요")
    url_result = git("remote", "get-url", "--push", remote)
    if url_result.returncode:
        print(json.dumps({"success":False,"reason":"원격 저장소 없음"}))
        return
    url = url_result.stdout.strip()
    if "://" in url:
        parts = urlsplit(url)
        safe_url = urlunsplit((parts.scheme, parts.hostname or "", parts.path, "", ""))
    else:
        safe_url = re.sub(r"^[^@]+@", "", url)
    head = git("rev-parse", "HEAD").stdout.strip()
    summary = {"branch":branch,"remote":remote,"destination":merge,"remote_url":safe_url,"head":head}
    action = request.get("action", "info")
    if action == "info":
        summary["staged_paths"] = git("diff", "--cached", "--name-only").stdout.splitlines()
        print(json.dumps(summary, ensure_ascii=False))
        return
    if action not in {"dry_run_push","push"} or request.get("expected_head") != head:
        raise ValueError("작업/커밋 해시 확인 필요")
    args = ["push"]
    if action == "dry_run_push":
        args.append("--dry-run")
    args.extend([remote, "HEAD:" + merge])
    result = git(*args, timeout=45)
    summary.update(success=result.returncode == 0, action=action,
        stdout=clean(result.stdout), stderr=clean(result.stderr))
    if action == "push" and result.returncode == 0:
        verify = git("ls-remote", "--heads", remote, merge)
        remote_head = verify.stdout.split()[0] if verify.stdout.strip() else ""
        summary.update(remote_head=remote_head, verified=remote_head == head)
    print(json.dumps(summary, ensure_ascii=False))
if __name__ == "__main__":
    main()
