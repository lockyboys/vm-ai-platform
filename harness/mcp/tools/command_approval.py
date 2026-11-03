"""실행 전 위험 명령 탐지·승인 확인 (2026-10-25 LuckyBoys: "승인 기능을 붙이고, 무슨 명령어를 쓰는지 반드시 표시").

mcp_codex_apps_run_python_source가 실행할 파이썬 파일과, 그 파일이 import하는 프로젝트 내부 모듈을 읽어
sudo·ssh·curl 같은 위험 명령과 파이썬 네트워크 모듈 사용을 찾는다.
    - 찾은 명령은 dry-run·실행 결과에 항상 표시한다(commands_detected: 명령·파일·줄·원문).
    - 실행할 때는 호출자가 approved_commands로 '찾은 명령 이름 전체'를 정확히 넘겨야만 실행한다.
      (하나라도 빠지거나 다르면 실행하지 않고 approval_required=True로 돌려준다.)
    - config.py 안의 명령 목록(예: systemd_run_command = ["sudo", ...])을 쓰는 파일도 그 키 이름으로 잡는다.

한계(미확인으로 보고할 것): 정적 텍스트 검사라서 문자열을 조립하거나(eval·base64 등) 외부 파일에서 읽는 명령은
놓칠 수 있다. 서버 쪽 최종 방어는 sudoers 허용 목록이다.
설정: 루트 config.py SPS_EXECUTION_APPROVAL (일반 지침 4). DB 사용 없음.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import config

_IMPORT = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))", re.MULTILINE)


def _settings() -> dict[str, Any]:
    return config.SPS_EXECUTION_APPROVAL


def _shell_pattern(commands: Iterable[str]) -> re.Pattern:
    """따옴표로 시작하는 문자열의 첫 단어가 명령인 경우만 잡는다(주석·일반 문장의 단어는 제외)."""
    names = "|".join(re.escape(c) for c in sorted(commands, key=len, reverse=True))
    return re.compile(rf"""["']\s*({names})(?=[\s"'])""")


def _module_pattern(modules: Iterable[str]) -> re.Pattern:
    names = "|".join(re.escape(m) for m in sorted(modules, key=len, reverse=True))
    return re.compile(rf"^\s*(?:from\s+({names})(?:\.|\s)|import\s+({names})\b)", re.MULTILINE)


def config_command_keys(commands: Iterable[str]) -> dict[str, str]:
    """config.py의 dict 설정 안에서 값이 위험 명령으로 시작하는 키 → 명령. 예: {"systemd_run_command": "sudo"}."""
    wanted, found = set(commands), {}

    def walk(value: Any, key: str | None) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, str(k))
        elif isinstance(value, (list, tuple)) and value and isinstance(value[0], str) and key:
            if value[0] in wanted:
                found[key] = value[0]
        elif isinstance(value, str) and key and value.split(" ", 1)[0] in wanted:
            found[key] = value.split(" ", 1)[0]

    for name in dir(config):
        if name.isupper():
            walk(getattr(config, name), None)
    return found


def _local_module(root: Path, module: str) -> Path | None:
    """import 이름을 프로젝트 안 파일로 바꾼다(표준·외부 라이브러리, config 자체는 None)."""
    if module.split(".")[0] in {"config"}:
        return None
    base = root / Path(*module.split("."))
    for candidate in (base.with_suffix(".py"), base / "__init__.py"):
        if candidate.is_file():
            return candidate
    return None


def scan(source: Path, root: Path) -> list[dict[str, Any]]:
    """source와 그 프로젝트 내부 import(최대 깊이 설정)에서 위험 명령을 찾는다."""
    settings = _settings()
    shell = _shell_pattern(settings["shell_commands"])
    modules = _module_pattern(settings["python_modules"])
    config_keys = config_command_keys(settings["shell_commands"])
    found: list[dict[str, Any]] = []
    seen: set[Path] = set()
    queue: list[tuple[Path, int]] = [(source.resolve(), 0)]
    while queue:
        path, depth = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = str(path.relative_to(root)) if root in path.parents else str(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            hits = [m.group(1) for m in shell.finditer(line)]
            hits += [f"python:{m.group(1) or m.group(2)}" for m in modules.finditer(line)]
            hits += [f"{cmd}(config.{key})" for key, cmd in config_keys.items()
                     if f'"{key}"' in line or f"'{key}'" in line]
            if "shell=True" in line or re.search(r"\bos\.system\(", line):
                hits.append("shell")
            for command in hits:
                found.append({"command": command, "file": relative, "line": line_no, "text": line.strip()[:200]})
        if depth < int(settings["max_import_depth"]):
            for a, b in _IMPORT.findall(text):
                local = _local_module(root, a or b)
                if local is not None:
                    queue.append((local.resolve(), depth + 1))
    return found


def command_names(found: list[dict[str, Any]]) -> list[str]:
    """승인에 필요한 명령 이름 목록(정렬·중복 제거). 사용자에게 보여주고 그대로 approved_commands로 받는다."""
    return sorted({item["command"] for item in found})


def approval_matches(found: list[dict[str, Any]], approved: Iterable[str] | None) -> bool:
    """찾은 명령이 없거나, 승인 목록이 찾은 명령 이름 전체와 정확히 같을 때만 True."""
    names = command_names(found)
    return not names or sorted(set(approved or [])) == names
