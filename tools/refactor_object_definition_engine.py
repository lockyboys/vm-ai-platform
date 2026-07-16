from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GENERATOR_PATH = (
    PROJECT_ROOT
    / "engine"
    / "generator"
    / "object_definition_generator.py"
)

ENGINE_PATH = (
    PROJECT_ROOT
    / "engine"
    / "object_definition_engine.py"
)

ADAPTER_PATH = (
    PROJECT_ROOT
    / "engine"
    / "runtime"
    / "object_definition_runtime_adapter.py"
)


THIN_GENERATOR_SOURCE = '''\
"""
SPS Object Definition Generator

Responsibility:
    확정된 Object Definition Row를 sp_object에 저장한다.

Rules:
    - Request 정규화를 수행하지 않는다.
    - Repository 검증을 수행하지 않는다.
    - Identifier를 발급하지 않는다.
    - Transaction을 제어하지 않는다.
    - Lock을 제어하지 않는다.
    - Object 생성 판단을 수행하지 않는다.
"""

from __future__ import annotations

from typing import Any

from common.database import CommonDatabase


class ObjectDefinitionGenerator:
    """확정된 Object Definition을 Repository에 저장한다."""

    def __init__(
        self,
        database: CommonDatabase,
    ) -> None:
        if database is None:
            raise ValueError(
                "ObjectDefinitionGenerator requires a database "
                "owned by ObjectDefinitionEngine."
            )

        self.database = database

    def generate(
        self,
        *,
        object_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """
        ObjectDefinitionEngine이 검증하고 확정한 데이터를 저장한다.

        Transaction의 시작, Commit, Rollback은 Engine이 소유한다.
        """
        affected = self.database.execute(
            """
            INSERT INTO sp_object
            (
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_description,
                parent_object_id,
                object_level,
                sort_no,
                status_code,
                active_yn,
                version_no,
                lifecycle_id,
                created_by,
                created_dt,
                updated_by,
                updated_dt,
                deleted_by,
                deleted_dt,
                client_ip,
                program_id,
                target_identifier_field,
                sequence_scope_code,
                sequence_length,
                change_reason,
                identifier_target_code
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP,
                %s,
                CURRENT_TIMESTAMP,
                NULL,
                NULL,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                object_id,
                request["object_code"],
                request["object_name"],
                request["business_code"],
                request["domain_code"],
                request["object_type_code"],
                request.get("object_description"),
                request.get("parent_object_id"),
                request["object_level"],
                request.get("sort_no", 0),
                request["status_code"],
                request["active_yn"],
                request["version_no"],
                request.get("lifecycle_id"),
                request["created_by"],
                request["updated_by"],
                request["client_ip"],
                request["program_id"],
                request.get("target_identifier_field"),
                request["sequence_scope_code"],
                request["sequence_length"],
                request.get("change_reason"),
                request["identifier_target_code"],
            ),
        )

        if affected != 1:
            raise RuntimeError(
                "sp_object generation failed. "
                f"object_id={object_id}, "
                f"affected_rows={affected}"
            )

        return {
            "success": True,
            "status": "GENERATED",
            "generator": self.__class__.__name__,
            "object_id": object_id,
            "object_code": request["object_code"],
            "affected_rows": affected,
        }
'''


def backup(path: Path, timestamp: str) -> Path | None:
    if not path.exists():
        return None

    backup_path = path.with_name(
        f"{path.name}.bak_{timestamp}"
    )

    shutil.copy2(path, backup_path)
    return backup_path


def build_engine_source(source: str) -> str:
    required_tokens = (
        "class ObjectDefinitionGenerator:",
        "self.identifier_engine = IdentifierEngine(self.database)",
        "self._insert_object(",
        "    def _insert_object(",
    )

    missing = [
        token
        for token in required_tokens
        if token not in source
    ]

    if missing:
        raise RuntimeError(
            "Source structure does not match expected version. "
            f"missing_tokens={missing}"
        )

    source = source.replace(
        "SPS Object Definition Generator",
        "SPS Object Definition Engine",
        1,
    )

    source = source.replace(
        "class ObjectDefinitionGenerator:",
        "class ObjectDefinitionEngine:",
        1,
    )

    source = source.replace(
        '"""신규 Object Definition Repository Generator."""',
        '"""Object Definition 생성 흐름과 Transaction을 통제한다."""',
        1,
    )

    identifier_import = (
        "from engine.identifier_engine import IdentifierEngine"
    )

    generator_import = (
        "from engine.generator.object_definition_generator "
        "import ObjectDefinitionGenerator"
    )

    source = source.replace(
        identifier_import,
        f"{identifier_import}\n{generator_import}",
        1,
    )

    initializer = (
        "        self.identifier_engine = "
        "IdentifierEngine(self.database)"
    )

    source = source.replace(
        initializer,
        (
            f"{initializer}\n"
            "        self.generator = "
            "ObjectDefinitionGenerator(self.database)"
        ),
        1,
    )

    source = source.replace(
        "              → sp_object Save",
        "              → ObjectDefinitionGenerator 실행",
        1,
    )

    source = source.replace(
        "            self._insert_object(\n",
        "            self.generator.generate(\n",
        1,
    )

    method_marker = "    def _insert_object("

    method_start = source.find(method_marker)

    if method_start < 0:
        raise RuntimeError(
            "_insert_object method boundary not found."
        )

    # _insert_object는 기존 파일의 마지막 Method이므로
    # Engine에서 제거하고 Generator로 이동한다.
    source = source[:method_start].rstrip() + "\n"

    return source


def patch_adapter(source: str) -> str:
    old_module = (
        "engine.generator.object_definition_generator"
    )
    new_module = (
        "engine.object_definition_engine"
    )

    if old_module not in source:
        raise RuntimeError(
            "Runtime Adapter import path was not found."
        )

    source = source.replace(
        old_module,
        new_module,
    )

    source = source.replace(
        "ObjectDefinitionGenerator",
        "ObjectDefinitionEngine",
    )

    return source


def main() -> int:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not GENERATOR_PATH.exists():
        raise FileNotFoundError(
            f"Generator source not found: {GENERATOR_PATH}"
        )

    if not ADAPTER_PATH.exists():
        raise FileNotFoundError(
            f"Runtime Adapter not found: {ADAPTER_PATH}"
        )

    generator_backup = backup(
        GENERATOR_PATH,
        timestamp,
    )

    adapter_backup = backup(
        ADAPTER_PATH,
        timestamp,
    )

    original_generator_source = (
        GENERATOR_PATH.read_text(encoding="utf-8")
    )

    original_adapter_source = (
        ADAPTER_PATH.read_text(encoding="utf-8")
    )

    engine_source = build_engine_source(
        original_generator_source
    )

    adapter_source = patch_adapter(
        original_adapter_source
    )

    ENGINE_PATH.write_text(
        engine_source,
        encoding="utf-8",
    )

    GENERATOR_PATH.write_text(
        THIN_GENERATOR_SOURCE,
        encoding="utf-8",
    )

    ADAPTER_PATH.write_text(
        adapter_source,
        encoding="utf-8",
    )

    print("=" * 78)
    print("Object Definition Engine / Generator Refactoring")
    print("=" * 78)
    print(f"ENGINE            : {ENGINE_PATH.relative_to(PROJECT_ROOT)}")
    print(f"GENERATOR         : {GENERATOR_PATH.relative_to(PROJECT_ROOT)}")
    print(f"RUNTIME ADAPTER   : {ADAPTER_PATH.relative_to(PROJECT_ROOT)}")
    print(f"GENERATOR BACKUP  : {generator_backup}")
    print(f"ADAPTER BACKUP    : {adapter_backup}")
    print("STATUS             : OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
