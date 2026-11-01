"""블라인드 리뷰 job 셸(pid)의 자식 프로세스를 /proc에서 읽기 전용으로 찾는다 (2026-11-01).

이유: kill <셸 pid>는 셸이 자식(python 워커)이 끝날 때까지 신호 처리를 미뤄 워커가 계속 돈다.
동작: /proc/*/stat의 부모 pid를 비교해 자식 pid와 명령줄을 출력만 한다(종료시키지 않음).
입력(stdin JSON): {"pid": <셸 pid>}
"""
import json
import sys
from pathlib import Path

parent = int(json.loads(sys.stdin.read() or "{}")["pid"])  # 잘못된 입력이면 여기서 예외로 중단
found = []
for stat in Path("/proc").glob("[0-9]*/stat"):
    try:
        fields = stat.read_text().rsplit(")", 1)[1].split()
        if int(fields[1]) == parent:  # fields[1] = 부모 pid(ppid)
            pid = int(stat.parent.name)
            cmd = (stat.parent / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            found.append({"pid": pid, "cmdline": cmd[:200]})
    except (OSError, IndexError, ValueError):
        continue  # 그 사이 끝난 프로세스는 건너뛴다
print(json.dumps({"parent": parent, "parent_alive": Path(f"/proc/{parent}").exists(), "children": found},
                 ensure_ascii=False, indent=2))
