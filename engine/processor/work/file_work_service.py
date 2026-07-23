"""File-based SPS Work service for the demonstration workflow."""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine
from engine.runtime.file_runtime_adapter import FileRuntimeAdapter
from engine.processor.word.document_generation_service import (
    DocumentGenerationRequest,
    DocumentGenerationService,
)

SEOUL_TIME_ZONE: Final[str] = "Asia/Seoul"
DEFAULT_WORK_OUTPUT_ROOT: Final[Path] = Path("output/file_work")
SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset({".pdf", ".jpg", ".jpeg", ".png"})
PROGRAM_ID: Final[str] = "file_work_service.py"


@dataclass(frozen=True, slots=True)
class FileWorkResult:
    work_session_id: str
    work_item_id: str
    source_object_id: str
    source_path: Path
    extracted_text_path: Path
    docx_path: Path
    report_path: Path
    extracted_text_length: int
    asset_ids: tuple[str, ...]


class FileWorkService:
    """Process one uploaded PDF/image and persist the official Work chain."""

    def __init__(self, *, output_root: str | Path = DEFAULT_WORK_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root).resolve()
        self.document_service = DocumentGenerationService(output_root=self.output_root)

    def process(self, *, upload_path: Path, requested_by: str, client_ip: str) -> FileWorkResult:
        source = upload_path.resolve()
        self._validate_source(source)

        database = CommonDatabase(database_role="STORY_PLATFORM")
        try:
            identifier_engine = IdentifierEngine(database)
            source_object = self._resolve_source_object(database, source)
            database.begin()
            try:
                work_session_id = identifier_engine.generate(
                    "WORK_SESSION", manage_transaction=False
                )
                work_item_id = identifier_engine.generate(
                    "WORK_ITEM", manage_transaction=False
                )
                asset_ids = tuple(
                    identifier_engine.generate("WORK_ASSET", manage_transaction=False)
                    for _ in range(4)
                )

                artifact_directory = self.output_root / work_session_id
                artifact_directory.mkdir(parents=True, exist_ok=False)
                source_path = artifact_directory / source.name
                shutil.copy2(source, source_path)

                extracted_text, extractor_name = self._extract_text(source_path)
                extracted_text_path = artifact_directory / "extracted_text.txt"
                extracted_text_path.write_text(extracted_text, encoding="utf-8")

                now = datetime.now(ZoneInfo(SEOUL_TIME_ZONE))
                generation = self.document_service.generate(
                    request=self._build_document_request(
                        source_name=source.name,
                        work_session_id=work_session_id,
                        work_item_id=work_item_id,
                        extracted_text=extracted_text,
                    ),
                    requested_by=requested_by,
                )
                report_path = self._write_execution_report(
                    artifact_directory=artifact_directory,
                    source_path=source_path,
                    extracted_text_path=extracted_text_path,
                    docx_path=generation.docx_path,
                    work_session_id=work_session_id,
                    work_item_id=work_item_id,
                    asset_ids=asset_ids,
                    source_object_id=str(source_object["object_id"]),
                    extractor_name=extractor_name,
                    extracted_text_length=len(extracted_text),
                    requested_by=requested_by,
                    generated_dt=now,
                )

                self._insert_work_rows(
                    database=database,
                    work_session_id=work_session_id,
                    work_item_id=work_item_id,
                    source_object_id=str(source_object["object_id"]),
                    source_name=source.name,
                    source_path=source_path,
                    extracted_text_path=extracted_text_path,
                    docx_path=generation.docx_path,
                    report_path=report_path,
                    asset_ids=asset_ids,
                    extractor_name=extractor_name,
                    extracted_text_length=len(extracted_text),
                    requested_by=requested_by,
                    client_ip=client_ip,
                    now=now,
                )
                self._verify_work_rows(
                    database=database,
                    work_session_id=work_session_id,
                    work_item_id=work_item_id,
                    asset_ids=asset_ids,
                )
                database.commit()
            except Exception:
                database.rollback()
                raise
        finally:
            database.close()

        runtime_result = FileRuntimeAdapter().execute(str(source_path))
        collection_result = runtime_result["mongodb_collection_generator_result"]
        document_result = runtime_result["mongodb_document_result"]
        if collection_result["status"] != "SUCCESS":
            raise RuntimeError("MongoDB Collection 생성에 실패했습니다.")
        if document_result["status"] != "SUCCESS":
            raise RuntimeError(
                f"MongoDB Document 저장에 실패했습니다: {document_result.get('message')}"
            )

        return FileWorkResult(
            work_session_id=work_session_id,
            work_item_id=work_item_id,
            source_object_id=str(source_object["object_id"]),
            source_path=source_path,
            extracted_text_path=extracted_text_path,
            docx_path=generation.docx_path,
            report_path=report_path,
            extracted_text_length=len(extracted_text),
            asset_ids=asset_ids,
        )

    @staticmethod
    def _validate_source(source: Path) -> None:
        if not source.is_file():
            raise ValueError("업로드 파일을 찾을 수 없습니다.")
        if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError("PDF, JPG, JPEG, PNG 파일만 업로드할 수 있습니다.")

    @staticmethod
    def _resolve_source_object(database: CommonDatabase, source: Path) -> dict[str, object]:
        object_code = "DOCUMENT" if source.suffix.lower() == ".pdf" else "IMAGE"
        row = database.fetch_one(
            """
            SELECT object_id, object_code
            FROM sp_object
            WHERE object_code = %s
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (object_code,),
        )
        if not row:
            raise RuntimeError(f"Source Object metadata is not registered: {object_code}")
        return row

    @staticmethod
    def _extract_text(source_path: Path) -> tuple[str, str]:
        if source_path.suffix.lower() == ".pdf":
            try:
                from engine.analyzer.document_analyzer import extract_document_text
            except ImportError:
                from document_analyzer import extract_document_text
            text = extract_document_text(source_path)
            return (text or "").strip(), "document_analyzer.extract_document_text"

        try:
            from PIL import Image
            import pytesseract
        except ImportError as error:
            raise RuntimeError("이미지 OCR 실행 의존성을 찾을 수 없습니다.") from error

        try:
            with Image.open(source_path) as image:
                text = pytesseract.image_to_string(image, lang="kor+eng")
        except Exception as error:
            raise RuntimeError(f"이미지 OCR에 실패했습니다: {error}") from error
        return (text or "").strip(), "pytesseract.image_to_string"

    @staticmethod
    def _build_document_request(
        *,
        source_name: str,
        work_session_id: str,
        work_item_id: str,
        extracted_text: str,
    ) -> DocumentGenerationRequest:
        preview = extracted_text[:3000] if extracted_text else "(추출된 텍스트가 없습니다.)"
        return DocumentGenerationRequest(
            title=f"SPS 파일 처리 리포트_{Path(source_name).stem}",
            part_title="파일 기반 Document Intelligence 처리",
            philosophy=(
                "사람이 파일을 제공하고, 저장소(Repository)가 처리 근거를 기억하며, "
                "Engine(엔진)이 내용을 해석하고, 생성기(Generator)가 공식 리포트를 출력한다."
            ),
            chapter_title="업로드 파일 분석과 Repository 저장",
            section_title="PDF·이미지 추출 결과",
            body=(
                f"- 원본 파일: {source_name}\n"
                f"- Work Session ID: {work_session_id}\n"
                f"- Work Item ID: {work_item_id}\n"
                f"- 추출 텍스트\n{preview}"
            ),
        )

    def _insert_work_rows(
        self,
        *,
        database: CommonDatabase,
        work_session_id: str,
        work_item_id: str,
        source_object_id: str,
        source_name: str,
        source_path: Path,
        extracted_text_path: Path,
        docx_path: Path,
        report_path: Path,
        asset_ids: tuple[str, ...],
        extractor_name: str,
        extracted_text_length: int,
        requested_by: str,
        client_ip: str,
        now: datetime,
    ) -> None:
        request_json = json.dumps(
            {
                "source_file_name": source_name,
                "source_extension": source_path.suffix.lower(),
                "requested_by": requested_by,
            },
            ensure_ascii=False,
        )
        response_json = json.dumps(
            {
                "extractor": extractor_name,
                "extracted_text_length": extracted_text_length,
                "asset_count": len(asset_ids),
            },
            ensure_ascii=False,
        )
        database.execute(
            """
            INSERT INTO sp_work_session
            (work_session_id, worker_object_id, work_type_code, work_name,
             work_description, work_goal, work_status_code, work_result_code,
             request_json, response_json, started_dt, completed_dt,
             created_by, updated_by, client_ip, program_id)
            VALUES
            (%s, %s, 'PROCESS_FILE', %s, %s, %s, 'COMPLETED', 'SUCCESS',
             %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                work_session_id, source_object_id, f"파일 처리: {source_name}",
                "업로드 파일을 분석하고 공식 Work Asset으로 기록한다.",
                "원본·추출 텍스트·DOCX·실행 리포트를 추적 가능하게 저장한다.",
                request_json, response_json, now, now,
                requested_by, requested_by, client_ip, PROGRAM_ID,
            ),
        )
        database.execute(
            """
            INSERT INTO sp_work_item
            (work_item_id, work_session_id, work_step_no, work_item_name,
             work_item_description, work_status_code, work_result_code,
             request_json, response_json, started_dt, completed_dt,
             created_by, updated_by, client_ip, program_id)
            VALUES
            (%s, %s, 1, %s, %s, 'COMPLETED', 'SUCCESS',
             %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                work_item_id, work_session_id, "파일 읽기·리포트 생성",
                "PDF 텍스트 추출 또는 이미지 OCR 후 DOCX와 실행 리포트를 생성한다.",
                request_json, response_json, now, now,
                requested_by, requested_by, client_ip, PROGRAM_ID,
            ),
        )
        assets = (
            ("SOURCE_FILE", source_path, {"sha256": self._sha256(source_path)}),
            ("EXTRACTED_TEXT", extracted_text_path, {"extractor": extractor_name}),
            ("DOCX_REPORT", docx_path, {"work_session_id": work_session_id}),
            ("MARKDOWN_REPORT", report_path, {"work_item_id": work_item_id}),
        )
        for asset_id, (asset_type_code, asset_path, metadata) in zip(asset_ids, assets, strict=True):
            database.execute(
                """
                INSERT INTO sp_work_asset
                (work_asset_id, work_item_id, asset_type_code, asset_name, asset_path,
                 asset_size, asset_status_code, metadata_json,
                 created_by, updated_by, client_ip, program_id)
                VALUES
                (%s, %s, %s, %s, %s, %s, 'STORED', %s, %s, %s, %s, %s)
                """,
                (
                    asset_id, work_item_id, asset_type_code, asset_path.name, str(asset_path),
                    asset_path.stat().st_size, json.dumps(metadata, ensure_ascii=False),
                    requested_by, requested_by, client_ip, PROGRAM_ID,
                ),
            )

    @staticmethod
    def _verify_work_rows(
        *,
        database: CommonDatabase,
        work_session_id: str,
        work_item_id: str,
        asset_ids: tuple[str, ...],
    ) -> None:
        session_row = database.fetch_one(
            "SELECT work_session_id FROM sp_work_session WHERE work_session_id = %s",
            (work_session_id,),
        )
        item_row = database.fetch_one(
            "SELECT work_item_id FROM sp_work_item WHERE work_item_id = %s",
            (work_item_id,),
        )
        placeholders = ", ".join(["%s"] * len(asset_ids))
        asset_rows = database.fetch_all(
            f"SELECT work_asset_id FROM sp_work_asset WHERE work_asset_id IN ({placeholders})",
            asset_ids,
        )
        if not session_row or not item_row or len(asset_rows) != len(asset_ids):
            raise RuntimeError("Work Repository 저장 검증에 실패했습니다.")

    @staticmethod
    def _write_execution_report(
        *,
        artifact_directory: Path,
        source_path: Path,
        extracted_text_path: Path,
        docx_path: Path,
        work_session_id: str,
        work_item_id: str,
        asset_ids: tuple[str, ...],
        source_object_id: str,
        extractor_name: str,
        extracted_text_length: int,
        requested_by: str,
        generated_dt: datetime,
    ) -> Path:
        report_path = artifact_directory / "file_work_execution_report.md"
        report_path.write_text(
            "\n".join(
                (
                    "# SPS 파일 처리 실행 리포트",
                    "",
                    f"- 처리 시각: {generated_dt.strftime('%Y-%m-%d %H:%M:%S KST')}",
                    f"- 요청자: {requested_by}",
                    f"- Source Object ID: {source_object_id}",
                    f"- Work Session ID: {work_session_id}",
                    f"- Work Item ID: {work_item_id}",
                    f"- 추출기: {extractor_name}",
                    f"- 추출 텍스트 길이: {extracted_text_length}",
                    "",
                    "## Repository 저장 검증",
                    "",
                    "- [x] sp_work_session 저장",
                    "- [x] sp_work_item 저장",
                    "- [x] sp_work_asset 원본 파일 저장",
                    "- [x] sp_work_asset 추출 텍스트 저장",
                    "- [x] sp_work_asset DOCX 리포트 저장",
                    "- [x] sp_work_asset Markdown 리포트 저장",
                    "",
                    "## Asset",
                    "",
                    f"- SOURCE_FILE: {asset_ids[0]} | {source_path}",
                    f"- EXTRACTED_TEXT: {asset_ids[1]} | {extracted_text_path}",
                    f"- DOCX_REPORT: {asset_ids[2]} | {docx_path}",
                    f"- MARKDOWN_REPORT: {asset_ids[3]} | {report_path}",
                )
            ),
            encoding="utf-8",
        )
        return report_path

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
