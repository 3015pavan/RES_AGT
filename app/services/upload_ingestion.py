from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import AppError
from app.db.supabase_repo import SupabaseRepository
from app.models.schemas import SourceType
from app.services.advanced_llm_parser import AdvancedLLMParser
from app.services.embeddings import EmbeddingService
from app.services.normalization import extract_student_rows, normalize_result_records
from app.services.parsers import SUPPORTED_MIME_TYPES, chunk_text, parse_pdf_text, parse_tabular

BLOCKED_SIGNATURES = [
    b"<script",
    b"javascript:",
    b"powershell -enc",
    b"cmd.exe /c",
]
MAX_VECTOR_CHUNKS_PER_UPLOAD = 60


class UploadIngestionService:
    def __init__(
        self,
        settings: Settings,
        repository: SupabaseRepository,
        embedding_service: EmbeddingService,
        max_upload_mb: int,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.embedding_service = embedding_service
        self.max_upload_mb = max_upload_mb
        self.advanced_parser = AdvancedLLMParser(settings)

    async def ingest(
        self,
        file: UploadFile,
        source_type: SourceType = SourceType.upload,
        source_ref: str | None = None,
    ) -> dict[str, Any]:
        file_bytes = await file.read()
        file_name = file.filename or "upload"
        mime_type = file.content_type or "application/octet-stream"

        if len(file_bytes) > self.max_upload_mb * 1024 * 1024:
            raise AppError(
                code="FILE_TOO_LARGE",
                message=f"Upload exceeds max size of {self.max_upload_mb} MB",
                status_code=413,
            )

        if mime_type not in SUPPORTED_MIME_TYPES:
            raise AppError(code="UNSUPPORTED_MEDIA_TYPE", message=f"Unsupported mime type: {mime_type}", status_code=415)

        lower_bytes = file_bytes.lower()
        if any(sig in lower_bytes for sig in BLOCKED_SIGNATURES):
            raise AppError(code="MALICIOUS_CONTENT_DETECTED", message="Blocked unsafe file content", status_code=400)

        rows_ingested = 0
        extracted_text = ""
        normalized_rows_count = 0

        if file_name.lower().endswith((".csv", ".xlsx")):
            records = parse_tabular(file_bytes, file_name)
            rows_ingested = len(records)
            extracted_text = "\n".join(str(r) for r in records)
            normalized_rows = normalize_result_records(records)
            if not normalized_rows:
                parsed_text = self.advanced_parser.parse_document_with_llamaparse(file_bytes, file_name)
                if parsed_text:
                    extracted_text = parsed_text
                    normalized_rows = self.advanced_parser.parse_text(parsed_text)
            if not normalized_rows:
                normalized_rows = self.advanced_parser.parse_records(records)
            normalized_rows_count = len(normalized_rows)
            student_rows = extract_student_rows(records)
        elif file_name.lower().endswith(".pdf"):
            extracted_text = self.advanced_parser.parse_document_with_llamaparse(file_bytes, file_name) or parse_pdf_text(file_bytes)
            normalized_rows = self.advanced_parser.parse_text(extracted_text)
            normalized_rows_count = len(normalized_rows)
            student_rows = []
        else:
            raise AppError(code="UNSUPPORTED_FILE_TYPE", message="Unsupported file type", status_code=415)

        doc = self.repository.insert_document(
            source_type=source_type.value,
            source_ref=source_ref,
            file_name=file_name,
            mime_type=mime_type,
            content_text=extracted_text,
            metadata={"rows_ingested": rows_ingested, "normalized_rows": normalized_rows_count},
        )

        for student_row in student_rows:
            self.repository.upsert_student(
                usn=student_row["usn"],
                student_name=student_row["student_name"],
                semester=student_row["semester"],
                section=student_row["section"],
            )

        for row in normalized_rows:
            student = self.repository.upsert_student(
                usn=row.usn,
                student_name=row.student_name,
                semester=row.semester,
                section=row.section,
            )
            subject = self.repository.upsert_subject(
                subject_code=row.subject_code,
                subject_name=row.subject_name,
                semester=row.semester,
                credits=row.credits,
            )
            student_id = student.get("id")
            if not student_id:
                existing_student = self.repository.get_student_by_usn(row.usn)
                student_id = existing_student.get("id") if existing_student else None

            subject_id = subject.get("id")
            if not subject_id:
                existing_subject = self.repository.get_subject_by_code(row.subject_code)
                subject_id = existing_subject.get("id") if existing_subject else None

            if student_id and subject_id:
                self.repository.upsert_result(
                    student_id=student_id,
                    subject_id=subject_id,
                    exam_type=row.exam_type,
                    marks=row.marks,
                    max_marks=row.max_marks,
                    grade=row.grade,
                    pass_fail=row.pass_fail,
                    source_type=source_type.value,
                    source_ref=doc.get("id"),
                )

        chunks = chunk_text(extracted_text)
        if len(chunks) > MAX_VECTOR_CHUNKS_PER_UPLOAD:
            chunks = chunks[:MAX_VECTOR_CHUNKS_PER_UPLOAD]
        if chunks:
            vectors = self.embedding_service.embed_chunks(chunks)
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                self.repository.insert_vector_chunk(
                    document_id=doc["id"],
                    chunk_index=idx,
                    chunk_text=chunk,
                    embedding=vector,
                    source_type=source_type.value,
                    source_ref=source_ref,
                )

        return {
            "rows_ingested": rows_ingested,
            "documents_created": 1,
            "document_ids": [doc["id"]],
            "status": "success",
        }
