"""정확히 한 번 나오는 문자열만 바꾸는 소스 편집 도우미(source_patch가 적용되지 않을 때 사용).

입력(stdin JSON): {"path": "프로젝트 상대경로", "edits": [{"old": "...", "new": "..."}], "dry_run": true}
- 각 old는 파일에 정확히 1번 있어야 한다(0번/2번 이상이면 아무것도 바꾸지 않고 오류).
- dry_run=true면 검사만 하고 쓰지 않는다. 쓰기 전후 sha256을 출력한다.
- 원본 백업은 호출 전에 backup_files_before_edit.py로 만든다(사용자 지침: 원본 보존).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    relative = str(request.get("path") or "")
    target = (ROOT / relative).resolve()
    if ROOT not in target.parents or not target.is_file():
        raise ValueError("path must be an existing file inside the project")
    edits = request.get("edits") or []
    if not isinstance(edits, list) or not edits:
        raise ValueError("edits must be a non-empty list")
    text = target.read_text(encoding="utf-8")
    before = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for index, edit in enumerate(edits):
        old, new = edit.get("old"), edit.get("new")
        if not isinstance(old, str) or not old or not isinstance(new, str):
            raise ValueError(f"edit {index}: old/new must be text (old non-empty)")
        count = text.count(old)
        if count != 1:
            raise ValueError(f"edit {index}: old text found {count} times (must be exactly 1)")
        text = text.replace(old, new, 1)
    after = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if not request.get("dry_run", True):
        target.write_text(text, encoding="utf-8")
    print(json.dumps({"path": relative, "dry_run": bool(request.get("dry_run", True)),
                      "edits": len(edits), "before_sha256": before, "after_sha256": after}))


if __name__ == "__main__":
    main()
