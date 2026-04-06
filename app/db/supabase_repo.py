from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

from app.core.config import Settings


class SupabaseRepository:
    """Repository layer over Supabase tables.

    This foundation keeps all retrieval grounded in persisted data and never fabricates rows.
    """

    def __init__(self, settings: Settings) -> None:
        self.client: Client = create_client(settings.supabase_url, settings.supabase_key)

    def list_students(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        response = (
            self.client.table("students")
            .select("id,usn,student_name,semester,section,created_at")
            .range(offset, max(offset + limit - 1, offset))
            .execute()
        )
        return response.data or []

    def list_documents(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        response = (
            self.client.table("documents")
            .select("id,source_type,file_name,mime_type,created_at")
            .range(offset, max(offset + limit - 1, offset))
            .execute()
        )
        return response.data or []

    def insert_document(
        self,
        source_type: str,
        file_name: str,
        mime_type: str,
        content_text: str,
        metadata: dict[str, Any] | None = None,
        source_ref: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "source_type": source_type,
            "source_ref": source_ref,
            "file_name": file_name,
            "mime_type": mime_type,
            "content_text": content_text,
            "metadata": metadata or {},
        }
        response = self.client.table("documents").insert(payload).execute()
        return (response.data or [{}])[0]

    def insert_email_log(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table("email_logs").upsert(payload, on_conflict="message_id").execute()
        return (response.data or [{}])[0]

    def update_email_log(self, log_id: str, patch: dict[str, Any]) -> None:
        self.client.table("email_logs").update(patch).eq("id", log_id).execute()

    def mark_email_processed(self, log_id: str, response_status: str, response_error: str | None = None) -> None:
        patch = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "response_status": response_status,
            "response_error": response_error,
        }
        self.update_email_log(log_id, patch)

    def search_vector_chunks(
        self,
        embedding: list[float],
        limit: int = 5,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query_embedding": embedding, "match_count": limit}
        if source_type:
            params["source_filter"] = source_type
        response = self.client.rpc("match_vector_chunks", params).execute()
        return response.data or []

    def run_safe_sql(self, statement_name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute only pre-approved parameterized SQL via RPC wrappers.

        statement_name must map to a vetted RPC function in Supabase.
        """
        response = self.client.rpc(statement_name, {"payload": params}).execute()
        return response.data or []

    def upsert_student(self, usn: str, student_name: str | None, semester: int | None, section: str | None) -> dict[str, Any]:
        payload = {
            "usn": usn,
            "student_name": student_name,
            "semester": semester,
            "section": section,
        }
        response = self.client.table("students").upsert(payload, on_conflict="usn").execute()
        return (response.data or [{}])[0]

    def get_student_by_usn(self, usn: str) -> dict[str, Any] | None:
        response = self.client.table("students").select("id,usn").eq("usn", usn).limit(1).execute()
        rows = response.data or []
        return rows[0] if rows else None

    def upsert_subject(
        self,
        subject_code: str,
        subject_name: str,
        semester: int | None,
        credits: float | None,
    ) -> dict[str, Any]:
        payload = {
            "subject_code": subject_code,
            "subject_name": subject_name,
            "semester": semester,
            "credits": credits,
        }
        response = self.client.table("subjects").upsert(payload, on_conflict="subject_code").execute()
        return (response.data or [{}])[0]

    def get_subject_by_code(self, subject_code: str) -> dict[str, Any] | None:
        response = self.client.table("subjects").select("id,subject_code").eq("subject_code", subject_code).limit(1).execute()
        rows = response.data or []
        return rows[0] if rows else None

    def upsert_result(
        self,
        student_id: str,
        subject_id: str,
        exam_type: str | None,
        marks: float | None,
        max_marks: float | None,
        grade: str | None,
        pass_fail: str | None,
        source_type: str,
        source_ref: str | None,
    ) -> dict[str, Any]:
        payload = {
            "student_id": student_id,
            "subject_id": subject_id,
            "exam_type": exam_type,
            "marks": marks,
            "max_marks": max_marks,
            "grade": grade,
            "pass_fail": pass_fail,
            "source_type": source_type,
            "source_ref": source_ref,
        }
        response = self.client.table("results").upsert(
            payload,
            on_conflict="student_id,subject_id,exam_type,source_ref",
        ).execute()
        return (response.data or [{}])[0]

    def insert_vector_chunk(
        self,
        document_id: str,
        chunk_index: int,
        chunk_text: str,
        embedding: list[float],
        source_type: str,
        source_ref: str | None,
    ) -> None:
        self.client.table("vector_chunks").insert(
            {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "chunk_text": chunk_text,
                "embedding": embedding,
                "source_type": source_type,
                "source_ref": source_ref,
                "metadata": {},
            }
        ).execute()

    def has_blob_hash(self, content_hash: str) -> bool:
        response = self.client.table("ingested_blobs").select("id").eq("content_hash", content_hash).limit(1).execute()
        return bool(response.data)

    def record_blob_hash(self, source_type: str, source_ref: str | None, content_hash: str, file_name: str | None) -> None:
        self.client.table("ingested_blobs").insert(
            {
                "source_type": source_type,
                "source_ref": source_ref,
                "content_hash": content_hash,
                "file_name": file_name,
            }
        ).execute()

    def list_migration_versions(self) -> set[str]:
        response = self.client.table("schema_migrations").select("version").execute()
        versions = {row.get("version") for row in (response.data or []) if row.get("version")}
        return versions

    def insert_query_log(self, payload: dict[str, Any]) -> None:
        self.client.table("query_logs").insert(payload).execute()

    def insert_email_dead_letter(self, payload: dict[str, Any]) -> None:
        self.client.table("email_dead_letters").insert(payload).execute()
