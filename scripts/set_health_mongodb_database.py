# =============================================================================
# File Name   : scripts/set_health_mongodb_database.py
# Purpose     : Verify and restore the HEALTH MongoDB target database
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260830 | OpenAI | 검증된 MongoDB 관리자 계정으로 HEALTH 역할 DB를 복구함
# =============================================================================

from __future__ import annotations

import argparse
from pathlib import Path
from stat import S_IMODE
from urllib.parse import quote_plus

from dotenv import dotenv_values
from pymongo import MongoClient


ENV_PATH = Path("/data/vm_project/.env")
CONNECTION_TIMEOUT_MS = 5000


def _replace_settings(settings: dict[str, str]) -> None:
    output: list[str] = []
    written_keys: set[str] = set()

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        candidate = raw_line.strip()
        if candidate.startswith("export "):
            candidate = candidate[7:].lstrip()
        key = candidate.split("=", 1)[0].strip() if "=" in candidate else ""

        if key in settings:
            if key not in written_keys:
                output.append(f"{key}={settings[key]}")
                written_keys.add(key)
            continue
        output.append(raw_line)

    for key, value in settings.items():
        if key not in written_keys:
            output.append(f"{key}={value}")

    file_mode = S_IMODE(ENV_PATH.stat().st_mode)
    ENV_PATH.write_text("\n".join(output) + "\n", encoding="utf-8")
    ENV_PATH.chmod(file_mode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    arguments = parser.parse_args()
    target_database = arguments.database.strip()

    values = {
        key: value
        for key, value in dotenv_values(ENV_PATH).items()
        if value is not None
    }
    required_keys = (
        "MONGODB_HOST",
        "MONGODB_PORT",
        "MONGODB_USER",
        "MONGODB_PASSWORD",
    )
    missing_keys = [key for key in required_keys if not values.get(key)]
    if missing_keys:
        raise SystemExit("Missing settings: " + ", ".join(missing_keys))

    role_uri = (
        f"mongodb://{quote_plus(values['MONGODB_USER'])}:"
        f"{quote_plus(values['MONGODB_PASSWORD'])}@"
        f"{values['MONGODB_HOST']}:{values['MONGODB_PORT']}/"
        f"{quote_plus(target_database)}?authSource=admin"
    )
    client = MongoClient(
        role_uri,
        serverSelectionTimeoutMS=CONNECTION_TIMEOUT_MS,
    )
    try:
        client.admin.command("ping")
        collection_count = len(client[target_database].list_collection_names())
    except Exception as error:
        raise SystemExit(
            f"MongoDB verification failed; .env was not changed ({type(error).__name__})."
        ) from error
    finally:
        client.close()

    _replace_settings(
        {
            "MONGODB_DATABASE": target_database,
            "HEALTH_COMPANION_MONGODB_URI": role_uri,
            "HEALTH_COMPANION_MONGODB_DATABASE": target_database,
        }
    )
    print(f"HEALTH MongoDB database verified and updated; collection_count={collection_count}.")


if __name__ == "__main__":
    main()
