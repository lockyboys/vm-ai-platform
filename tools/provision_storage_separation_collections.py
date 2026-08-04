"""Storage separation MongoDB collection provisioning entry point.

File Story:
    Storage Separation Target 공통코드 계약으로 MongoDB Collection과 Index를
    멱등 생성한다.

Change History:
    20260731 | SYSTEM | Storage Separation Collection Provisioning CLI를 추가한다.
    20260731 | SYSTEM | 직접 실행 시 프로젝트 최상위 import 경로를 동적으로 등록한다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase
from engine.storage.storage_separation_collection_provisioner import (
    StorageSeparationCollectionProvisioner,
    StorageSeparationContractRepository,
)


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """운영에서 명시한 공통코드 Group을 입력으로 받는다."""
    parser = argparse.ArgumentParser(
        description="Provision MongoDB collections from a storage separation contract.",
    )
    parser.add_argument(
        "--group-code",
        required=True,
        help="cm_common_code_group.group_code",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """계약 조회와 Collection·Index 생성을 실행한다."""
    parsed_arguments = parse_arguments(arguments)
    common_database = CommonDatabase(database_role="COMMON")
    databases: list[CommonDatabase] = [common_database]

    try:
        contracts = StorageSeparationContractRepository(
            common_database,
            group_code=parsed_arguments.group_code,
        ).load_active_contracts()

        def database_factory(database_role: str) -> CommonDatabase:
            database = CommonDatabase(
                database_role=database_role,
                connect_mariadb=False,
                connect_mongodb=True,
            )
            databases.append(database)
            return database

        result = StorageSeparationCollectionProvisioner(
            database_factory,
        ).provision(contracts)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        for database in reversed(databases):
            database.close()


if __name__ == "__main__":
    raise SystemExit(main())
