"""Table/Mongo Entity-Attribute contract extension (no implicit registrations).

Existing Table rows keep NULL Mongo bindings. Mongo Entities bind a Repository
Collection Object; Attributes retain column_name for legacy uniqueness and store
the exact BSON field path separately. Never infer a schema from sampled documents.
Connection settings remain owned by config.py through the common DB framework.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from common.common_function import normalize_required_text
from common.database import CommonDatabase

def read_contract_schema(database: CommonDatabase) -> dict[str, str]:
    """Read current table/field COMMENTS from an already role-resolved connection."""
    result = {}
    for table in ("sp_entity", "sp_attribute"):
        row = database.fetch_one(f"SHOW CREATE TABLE `{table}`")
        if not row:
            raise ValueError(f"Missing Repository table: {table}")
        result[table] = row["Create Table"]
    return result

def validate_storage_contract(
    entity: Mapping[str, Any],
    attributes: Sequence[Mapping[str, Any]],
    *,
    collection_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate explicit storage bindings before writing Entity/Attribute rows.

    collection_metadata MUST be resolved by the caller from the Collection
    Repository, never supplied as evidence by an untrusted request. This helper
    validates consistency, not the existence of that Repository row. It performs
    no database writes, ID generation, commit or inferred type certification.
    BSON types use the bson: prefix to distinguish them from MariaDB SQL types.
    Missing schemas are rejected rather than guessed from a document.
    """
    object_id = normalize_required_text(entity.get("object_id"), "object_id")
    collection_id = entity.get("mongodb_collection_id")
    if collection_id is not None:
        collection_id = normalize_required_text(collection_id, "mongodb_collection_id")
        if not collection_metadata:
            raise ValueError("Repository Collection metadata is required.")
        if (collection_metadata.get("mongodb_collection_id") != collection_id
                or collection_metadata.get("object_id") != object_id):
            raise ValueError("Entity/Collection Repository identity mismatch.")
    field_paths: list[str] = []
    seen: set[str] = set()
    for attribute in attributes:
        if attribute.get("object_id") != object_id:
            raise ValueError("Attribute must belong to the Entity Object.")
        column = normalize_required_text(attribute.get("column_name"), "column_name")
        if len(column) > 150:
            raise ValueError("column_name exceeds the existing VARCHAR(150) contract.")
        data_type = normalize_required_text(attribute.get("data_type"), "data_type")
        path = attribute.get("mongodb_field_path")
        if collection_id is None:
            if path is not None or data_type.startswith("bson:"):
                raise ValueError("Table Attributes cannot contain Mongo bindings.")
            identity = column
        else:
            path = normalize_required_text(path, "mongodb_field_path")
            # Disallow operators, ambiguous components and paths beyond DB limits.
            if (len(path) > 150 or "\\x00" in path
                    or any(not part or part.startswith("$") for part in path.split("."))):
                raise ValueError("Invalid BSON field path.")
            if column != path:
                raise ValueError("Mongo column_name must equal mongodb_field_path.")
            if not data_type.startswith("bson:") or not data_type[5:].strip():
                raise ValueError("Explicit BSON type declaration is required.")
            identity = path
            field_paths.append(path)
        if identity in seen:
            raise ValueError("Duplicate Attribute field.")
        seen.add(identity)
    return {"storage_kind": "MONGODB" if collection_id is not None else "TABLE",
            "object_id": object_id, "field_paths": field_paths}

def contract_extension_ddl() -> dict[str, str]:
    """Return additive DDL; use role-resolved STORY connection and backup first.

    Existing rows/FKs/indexes/types/defaults remain unchanged. Nullable additions
    keep physical Table batches backward compatible. Only COMMENT semantics and
    explicit Mongo bindings change; this is not a Mongo Collection registration.
    """
    return {
        "sp_entity": """ALTER TABLE `sp_entity`
ADD COLUMN `mongodb_collection_id` VARCHAR(99) DEFAULT NULL COMMENT 'MongoDB Collection Identifier. Collection Repository에서 조회한 컬렉션 식별자. NULL은 기존 MariaDB Table Entity /  값이 있으면 등록된 Mongo Collection Object Entity이며 문서 ID를 사용하지 않는다.',
MODIFY COLUMN `object_id` VARCHAR(99) NOT NULL COMMENT 'Entity Object ID. 기존 MariaDB Table 또는 등록된 MongoDB Collection Object의 sp_object.object_id. 논리·물리 Entity가 공유하며 Mongo Document Instance ID와 구분한다.',
COMMENT='PURPOSE: Repository MariaDB Table 및 MongoDB Collection에 대응하는 Entity Object 정의를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: sp_object 및 Collection Repository. ENGINE_GUIDE: mongodb_collection_id NULL은 Table 계약 /  값이 있으면 Mongo Collection 계약. Mongo Entity는 SQL Table DDL 생성 대상에서 제외한다. 기존 Table 계약·FK·데이터를 보존한다.'""",
        "sp_attribute": """ALTER TABLE `sp_attribute`
ADD COLUMN `mongodb_field_path` VARCHAR(150) DEFAULT NULL COMMENT 'MongoDB BSON Field Path. Collection Entity의 명시적 필드 경로(예: audit.created_dt) /  NULL은 기존 MariaDB Column. 표본 문서만으로 필수 여부·형식을 추정하지 않는다.',
MODIFY COLUMN `object_id` VARCHAR(99) NOT NULL COMMENT 'Entity Object ID. MariaDB Table 또는 등록된 MongoDB Collection Object ID. 소속 sp_entity와 동일 Object 범위를 공유한다.',
MODIFY COLUMN `column_name` VARCHAR(150) NOT NULL COMMENT 'MariaDB에서는 실제 물리 Column 명. Mongo Collection에서는 mongodb_field_path와 동일한 BSON 필드 경로를 기존 유일성 계약을 위해 유지한다. SQL DDL 생성 전에 Entity의 mongodb_collection_id를 확인한다.',
MODIFY COLUMN `data_type` VARCHAR(99) NOT NULL COMMENT 'MariaDB Column은 기존 SQL Data Type. Mongo Collection 필드는 명시적 bson:타입 선언(예: bson:string, bson:date)을 사용한다. Mongo BSON 타입을 MariaDB SQL 타입으로 해석하지 않는다.',
COMMENT='PURPOSE: Entity의 MariaDB Column 또는 MongoDB BSON Field Attribute 정의를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: Entity·Collection의 명시적 스키마. ENGINE_GUIDE: Mongo Entity는 mongodb_field_path와 bson:타입을 사용하며 SQL Table/Column DDL 생성에서 제외한다. 기존 Column 계약·FK·유일키·데이터를 보존한다.'""",
    }
