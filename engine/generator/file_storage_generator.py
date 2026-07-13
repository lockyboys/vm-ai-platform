import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


class FileStorageGenerator:
    """원본 Object 파일을 SPS Storage에 저장한다."""

    STORAGE_TYPE_MAP = {
        "DOCUMENT": "document",
        "IMAGE": "image",
        "VIDEO": "video",
        "AUDIO": "audio",
        "TEXT": "text",
        "POLICY": "policy",
    }

    def __init__(self):
        load_dotenv()

        self.storage_root = Path(
            os.getenv("SPS_STORAGE_ROOT", "/data/sps_storage")
        )

    def save(
        self,
        source_file_path: str,
        object_code: str,
        object_identifier: str,
    ) -> dict:
        source_file = Path(source_file_path).expanduser().resolve()

        if not source_file.is_file():
            raise FileNotFoundError(
                f"Source file not found: {source_file}"
            )

        storage_type = self.STORAGE_TYPE_MAP.get(
            object_code,
            "document",
        )

        now = datetime.now()
        target_directory = (
            self.storage_root
            / "raw"
            / storage_type
            / now.strftime("%Y")
            / now.strftime("%m")
            / now.strftime("%d")
        )
        target_directory.mkdir(parents=True, exist_ok=True)

        target_file = target_directory / (
            f"{object_identifier}{source_file.suffix.lower()}"
        )

        shutil.copy2(source_file, target_file)

        return {
            "generator": "FileStorageGenerator",
            "storage_type_code": storage_type.upper(),
            "storage_path": str(target_file),
            "original_file_name": source_file.name,
            "stored_file_name": target_file.name,
            "file_size": target_file.stat().st_size,
            "sha256": self._sha256(target_file),
            "stored_dt": now.astimezone().isoformat(
                timespec="seconds"
            ),
            "status": "SUCCESS",
        }

    @staticmethod
    def _sha256(file_path: Path) -> str:
        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()
