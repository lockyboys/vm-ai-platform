"""Storage Separation MongoDB Collection Provisioner.

File Story:
    Storage Separation Target 공통코드 계약을 읽어 MongoDB Collection과
    Document Index를 생성한다.

Change History:
    20260731 | SYSTEM | 공통코드 계약 기반 MongoDB Collection과 Index Provisioner를 추가한다.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from pymongo import ASCENDING, DESCENDING

from common.common_function import normalize_required_text
from common.database import CommonDatabase
from engine.generator.mongodb_collection_generator import MongoDBCollectionGenerator


class StorageSeparationContractRepository:
    """Storage Separation Target 공통코드 계약을 읽는다."""

    def __init__(
        self,
        common_database: CommonDatabase,
        *,
        group_code: str,
    ) -> None:
        self.common_database = common_database
        self.group_code = normalize_required_text(group_code, "group_code")

    def load_active_contracts(self) -> list[dict[str, Any]]:
        """활성 Storage Separation 계약을 sort 순서로 반환한다."""
        rows = self.common_database.fetch_all(
            """
            SELECT
                code,
                code_name,
                common_code_json
            FROM cm_common_code
            WHERE group_code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, code
            """,
            (self.group_code,),
        )
        return [self._parse_contract(row) for row in rows]

    @staticmethod
    def _parse_contract(row: Mapping[str, Any]) -> dict[str, Any]:
        try:
            contract = json.loads(str(row.get("common_code_json") or ""))
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError(
                "Storage separation common_code_json must be valid JSON. "
                f"code={row.get('code')}"
            ) from error

        if not isinstance(contract, dict):
            raise ValueError(
                "Storage separation common_code_json must be an object. "
                f"code={row.get('code')}"
            )

        required_fields = (
            "source_database_role",
            "source_table_name",
            "source_identifier_column_name",
            "mongodb_collection_name",
        )
        for field_name in required_fields:
            normalize_required_text(contract.get(field_name), field_name)

        return {
            "contract_code": normalize_required_text(row.get("code"), "code"),
            "contract_name": normalize_required_text(row.get("code_name"), "code_name"),
            **contract,
        }


class StorageSeparationCollectionProvisioner:
    """계약별 MongoDB Collection과 source identifier Index를 보장한다."""

    def __init__(
        self,
        database_factory: Callable[[str], CommonDatabase],
    ) -> None:
        self.database_factory = database_factory

    def provision(
        self,
        contracts: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, str]]:
        """모든 계약의 Collection과 Index를 멱등 생성한다."""
        database_by_role: dict[str, CommonDatabase] = {}
        results: list[dict[str, str]] = []

        for contract in contracts:
            database_role = normalize_required_text(
                contract.get("source_database_role"),
                "source_database_role",
            ).upper()
            collection_name = normalize_required_text(
                contract.get("mongodb_collection_name"),
                "mongodb_collection_name",
            )
            identifier_column_name = normalize_required_text(
                contract.get("source_identifier_column_name"),
                "source_identifier_column_name",
            )
            database = database_by_role.setdefault(
                database_role,
                self.database_factory(database_role),
            )
            generator = MongoDBCollectionGenerator(database=database)
            generator_result = generator.save({"collection_name": collection_name})
            if generator_result["status"] != "SUCCESS":
                raise RuntimeError(
                    "MongoDB collection provisioning failed. "
                    f"contract_code={contract.get('contract_code')}, "
                    f"collection_name={collection_name}, "
                    f"message={generator_result.get('message')}"
                )

            collection = database.get_collection(collection_name)
            collection.create_index(
                [(identifier_column_name, ASCENDING)],
                name=f"uq_{identifier_column_name}",
                unique=True,
            )
            collection.create_index(
                [("created_dt", DESCENDING)],
                name="ix_created_dt",
            )
            results.append(
                {
                    "contract_code": normalize_required_text(
                        contract.get("contract_code"),
                        "contract_code",
                    ),
                    "database_role": database_role,
                    "database_name": str(generator_result["database_name"]),
                    "collection_name": collection_name,
                    "identifier_index_name": f"uq_{identifier_column_name}",
                    "created_dt_index_name": "ix_created_dt",
                }
            )

        return results
