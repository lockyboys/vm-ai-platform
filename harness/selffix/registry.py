"""[등록] 자기 수리 대상 등록소 (2026-11-12 분리, 원본: self_repair_engine.py §4).

등록소(backend)
    config     : 루트 config.py 의 '# >>> SELF_REPAIR_TARGETS (generated)' ~ '# <<< SELF_REPAIR_TARGETS' 블록만
                 백업 → 결정적 직렬화 → compile 검사 → 원자적 교체. 블록 밖(다른 설정)은 건드리지 않는다.
    repository : MariaDB 테이블(config.SELF_REPAIR['repository_table']). 2차 작업(DDL 승인) 전이라 지금은
                 'repository backend unavailable' 오류를 명확히 돌려주고 아무것도 바꾸지 않는다.
DB: 이번 단계는 DB 를 연결·변경하지 않는다(repository 백엔드는 2차 DDL 승인 후 common/database.py 로 구현 예정).
"""
from __future__ import annotations

import ast
import os
import pprint
import re
import tempfile
from pathlib import Path
from typing import Any

import config as project_config  # 루트 공통 설정(일반 지침 4)
from harness.selffix.job_runner import PROJECT_ROOT, now_stamp
from harness.selffix.target_spec import validate_target

_SETTINGS = project_config.SELF_REPAIR
CONFIG_PATH = PROJECT_ROOT / "config.py"        # config 백엔드가 고치는 파일(테스트에서는 임시 사본으로 교체)
BLOCK_START = "# >>> SELF_REPAIR_TARGETS (generated)"
BLOCK_END = "# <<< SELF_REPAIR_TARGETS"
BLOCK_VARIABLE = "SELF_REPAIR_TARGETS"


def _render_block(targets: dict) -> str:
    """대상 목록을 결정적(정렬)인 파이썬 리터럴로 직렬화한다."""
    return f"{BLOCK_VARIABLE} = {pprint.pformat(targets, sort_dicts=True, width=100)}\n"


def _read_block(text: str) -> dict:
    """config 텍스트의 표시 블록에서 대상 목록을 읽는다(리터럴만 허용, 코드 실행 없음)."""
    has_start, has_end = BLOCK_START in text, BLOCK_END in text
    if not has_start and not has_end:
        return {}
    if has_start != has_end:
        raise ValueError("SELF_REPAIR_TARGETS block markers are incomplete")
    body = text.split(BLOCK_START, 1)[1].split(BLOCK_END, 1)[0]
    match = re.search(rf"^{BLOCK_VARIABLE}\s*=\s*", body, flags=re.MULTILINE)
    if match is None:
        return {}
    value = ast.literal_eval(body[match.end():].strip())
    if not isinstance(value, dict):
        raise ValueError("SELF_REPAIR_TARGETS must be a dict literal")
    return value


def _repository_unavailable() -> ValueError:
    """2차 작업(MariaDB 테이블 DDL 승인) 전까지 repository 백엔드는 명확히 거부한다."""
    return ValueError(f"repository backend unavailable: 2차 DDL 승인 필요 "
                      f"(table={_SETTINGS['repository_table']} 미생성, 지금은 config 백엔드만 사용)")


def _replace_block(text: str, targets: dict) -> tuple[str, str]:
    """표시 블록만 새 내용으로 바꾼 전체 텍스트와 동작(replace_block/append_block)을 돌려준다."""
    block = (f"{BLOCK_START}\n# 자동 생성: self_repair_target_register 가 관리한다. 손으로 고치지 말 것.\n"
             f"{_render_block(targets)}{BLOCK_END}\n")
    if BLOCK_START in text:
        head, rest = text.split(BLOCK_START, 1)
        tail = rest.split(BLOCK_END, 1)[1].lstrip("\n")
        return head + block + tail, "replace_block"
    return text + ("" if text.endswith("\n") else "\n") + "\n" + block, "append_block"


def register_target(spec: Any, backend: str = "config", overwrite: bool = False, dry_run: bool = True,
                    config_path: Path | str | None = None) -> dict:
    """대상을 등록한다. config 는 표시 블록만 원자적으로 교체, repository 는 2차 작업 전까지 명확히 거부."""
    if backend not in {"config", "repository"}:
        raise ValueError("backend must be 'config' or 'repository'")
    spec = validate_target(spec)
    if backend == "repository":
        raise _repository_unavailable()
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    original = path.read_text(encoding="utf-8")
    targets = _read_block(original)
    if spec["name"] in targets and not overwrite:
        raise ValueError(f"target already registered: {spec['name']} (overwrite=True 로만 교체)")
    new_text, action = _replace_block(original, {**targets, spec["name"]: spec})
    try:
        compile(new_text, str(path), "exec")       # 깨진 config 는 절대 쓰지 않는다
    except SyntaxError as error:
        raise ValueError(f"generated config does not compile: {error}") from error
    plan = {"dry_run": bool(dry_run), "backend": "config", "path": str(path), "target": spec["name"],
            "action": action, "overwrite": bool(overwrite and spec["name"] in targets), "spec": spec}
    if dry_run:
        return plan
    backup = path.with_name(f"{path.stem}_BACKUP_{now_stamp()}{path.suffix}")
    backup.write_text(original, encoding="utf-8")                      # 원본 보존(일반 지침 7)
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(new_text)
        os.chmod(temp_name, path.stat().st_mode & 0o777)
        os.replace(temp_name, path)                                    # 원자적 교체
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {**plan, "applied": True, "backup": str(backup)}


def list_targets() -> dict:
    """등록된 대상 목록. config 파일을 매번 다시 읽는다(서버 재시작 없이 등록 반영)."""
    targets = _read_block(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"targets": targets, "sources": {"config": True, "repository": str(_repository_unavailable())}}


def get_target(name: str) -> dict:
    """등록된 대상 하나를 검증해서 돌려준다. 미등록이면 ValueError(임의 실행 차단)."""
    targets = list_targets()["targets"]
    if name not in targets:
        raise ValueError(f"target not registered: {name}")
    return validate_target(targets[name])
