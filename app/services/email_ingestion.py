from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from email import message_from_bytes
from email.message import Message
from email.utils import parseaddr
from typing import Any

from app.core.security import validate_email_value
from app.db.supabase_repo import SupabaseRepository
from app.models.schemas import SourceType
from app.services.email_client import EmailClient
from app.services.embeddings import EmbeddingService
from app.services.parsers import chunk_text
from app.services.query_service import QueryService
from app.services.upload_ingestion import UploadIngestionService


class EmailIngestionService:
    def __init__(
        self,
        repository: SupabaseRepository,
        email_client: EmailClient,
        upload_service: UploadIngestionService,
        embedding_service: EmbeddingService,
        query_service: QueryService,
        poll_batch_size: int,
    ) -> None:
        self.repository = repository
        self.email_client = email_client
        self.upload_service = upload_service
        self.embedding_service = embedding_service
        self.query_service = query_service
        self.poll_batch_size = poll_batch_size

    async def poll_and_process(self) -> dict[str, int]:
        processed = 0
        failed = 0
        messages = self.email_client.poll_unread(self.poll_batch_size)
        for item in messages:
            try:
                await self._process_one(item)
                processed += 1
            except Exception as exc:
                raw = item.get("raw") or b""
                message_hash = hashlib.sha256(raw).hexdigest() if raw else None
                self.repository.insert_email_dead_letter(
                    {
                        "error_text": str(exc),
                        "raw_hash": message_hash,
                    }
                )
                failed += 1
        return {"processed": processed, "failed": failed}

    async def _process_one(self, item: dict[str, Any]) -> None:
        raw = item.get("raw")
        if not raw:
            return

        msg: Message = message_from_bytes(raw)
        sender_header = msg.get("From", "")
        _, sender = parseaddr(sender_header)
        sender = sender or sender_header
        validate_email_value(sender, "sender_email")
        subject = msg.get("Subject", "")
        message_id = msg.get("Message-ID", "")
        if not message_id:
            message_id = f"generated-{hashlib.sha256(raw).hexdigest()}"

        body_text = self._extract_text_body(msg)
        log_row = self.repository.insert_email_log(
            {
                "message_id": message_id,
                "sender_email": sender,
                "subject": subject or "(no subject)",
                "body_text": body_text,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "has_attachments": any(part.get_filename() for part in msg.walk()),
                "query_detected": self._looks_like_query(body_text),
                "query_text": body_text if self._looks_like_query(body_text) else None,
            }
        )

        doc = self.repository.insert_document(
            source_type=SourceType.email.value,
            source_ref=log_row.get("id"),
            file_name=f"email_{log_row.get('id', 'unknown')}.txt",
            mime_type="text/plain",
            content_text=body_text,
            metadata={"subject": subject, "sender": sender},
        )

        chunks = chunk_text(body_text)
        if chunks:
            vectors = self.embedding_service.embed_chunks(chunks)
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                self.repository.insert_vector_chunk(
                    document_id=doc["id"],
                    chunk_index=idx,
                    chunk_text=chunk,
                    embedding=vector,
                    source_type=SourceType.email.value,
                    source_ref=log_row.get("id"),
                )

        for part in msg.walk():
            filename = part.get_filename()
            payload = part.get_payload(decode=True)
            if filename and payload:
                content_hash = hashlib.sha256(payload).hexdigest()
                if self.repository.has_blob_hash(content_hash):
                    continue
                # Reuse the same ingest path for attachment content normalization.
                sanitized_name = os.path.basename(filename)
                faux = _InMemoryUploadFile(filename=sanitized_name, content_type=part.get_content_type(), content=payload)
                await self.upload_service.ingest(
                    faux,
                    source_type=SourceType.email,
                    source_ref=log_row.get("id"),
                )
                self.repository.record_blob_hash(
                    source_type=SourceType.email.value,
                    source_ref=log_row.get("id"),
                    content_hash=content_hash,
                    file_name=sanitized_name,
                )

        if self._looks_like_query(body_text):
            answer = self.query_service.ask(body_text, channel="email").get("final_response", "NO DATA AVAILABLE")
            await self.email_client.send_reply(
                to_email=sender,
                subject=f"Re: {subject}" if subject else "Query Response",
                body=answer,
            )
            if log_row.get("id"):
                self.repository.mark_email_processed(log_row["id"], response_status="sent")
        elif log_row.get("id"):
            self.repository.mark_email_processed(log_row["id"], response_status="processed")

    @staticmethod
    def _extract_text_body(msg: Message) -> str:
        if msg.is_multipart():
            parts = []
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain" and not part.get_filename():
                    payload = part.get_payload(decode=True) or b""
                    parts.append(payload.decode(errors="ignore"))
            return "\n".join(parts).strip()

        payload = msg.get_payload(decode=True) or b""
        return payload.decode(errors="ignore").strip()

    @staticmethod
    def _looks_like_query(text: str) -> bool:
        lowered = text.lower()
        triggers = ["marks", "top", "lowest", "sgpa", "report", "average", "who"]
        return any(token in lowered for token in triggers)


class _InMemoryUploadFile:
    def __init__(self, filename: str, content_type: str, content: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content
