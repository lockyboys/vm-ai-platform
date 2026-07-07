# =============================================================================
# File Name   : engine/runtime/file_runtime_adapter.py
# Purpose     : File input을 Object Runtime으로 연결하는 Adapter
# =============================================================================

from pathlib import Path
import importlib

import config
from engine.runtime.object_runtime_engine import ObjectRuntimeEngine


class FileRuntimeAdapter:
    def __init__(self):
        self.object_runtime_engine = ObjectRuntimeEngine()

    def execute(self, file_path: str):
        source_file = Path(file_path).expanduser().resolve()

        if not source_file.exists() or not source_file.is_file():
            raise FileNotFoundError(f"File not found: {source_file}")

        file_metadata = self._build_file_metadata(source_file)
        analyzer_result = self._run_analyzer(source_file, file_metadata)

        return self.object_runtime_engine.execute(
            object_code=file_metadata["object_code"],
            input_data={
                "source_type": "FILE",
                "file_metadata": file_metadata,
                "analyzer_result": analyzer_result,
            },
        )

    def _build_file_metadata(self, source_file: Path) -> dict:
        extension = source_file.suffix.lower()

        if extension in config.DOCUMENT_EXTENSIONS:
            object_code = "DOCUMENT"
            analyzer_module = "document_analyzer"
            analyzer_method = "extract_document_text"

        elif extension in config.IMAGE_EXTENSIONS:
            object_code = "IMAGE"
            analyzer_module = "image_analyzer"
            analyzer_method = "extract_text_from_image"

        elif extension in config.VIDEO_EXTENSIONS:
            object_code = "VIDEO"
            analyzer_module = "video_analyzer"
            analyzer_method = "extract_text_from_video"

        elif extension in config.AUDIO_EXTENSIONS:
            object_code = "AUDIO"
            analyzer_module = "audio_analyzer"
            analyzer_method = "transcribe_audio_to_text"

        else:
            object_code = "FILE"
            analyzer_module = None
            analyzer_method = None

        return {
            "file_path": str(source_file),
            "file_name": source_file.name,
            "file_stem": source_file.stem,
            "extension": extension,
            "file_size": source_file.stat().st_size,
            "object_code": object_code,
            "analyzer_module": analyzer_module,
            "analyzer_method": analyzer_method,
        }

    def _run_analyzer(self, source_file: Path, file_metadata: dict) -> dict:
        analyzer_module = file_metadata.get("analyzer_module")
        analyzer_method = file_metadata.get("analyzer_method")

        if not analyzer_module or not analyzer_method:
            return {
                "status": "SKIPPED",
                "reason": "Analyzer not defined",
                "text": "",
            }

        module = importlib.import_module(analyzer_module)
        method = getattr(module, analyzer_method)

        text = method(source_file)

        return {
            "status": "SUCCESS",
            "analyzer_module": analyzer_module,
            "analyzer_method": analyzer_method,
            "text": text or "",
        }


if __name__ == "__main__":
    file_path = input("File Path : ").strip().strip('"')
    adapter = FileRuntimeAdapter()
    result = adapter.execute(file_path)

    print("=" * 70)
    print("File Runtime Result")
    print("=" * 70)
    print(result)