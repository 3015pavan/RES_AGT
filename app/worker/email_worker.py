from __future__ import annotations

import asyncio
import logging
import signal

from app.core.config import get_settings
from app.db.supabase_repo import SupabaseRepository
from app.services.email_client import EmailClient
from app.services.email_ingestion import EmailIngestionService
from app.services.embeddings import EmbeddingService
from app.services.query_service import QueryService
from app.services.upload_ingestion import UploadIngestionService

logger = logging.getLogger(__name__)


async def run_email_worker_forever() -> None:
    settings = get_settings()
    repository = SupabaseRepository(settings)
    embeddings = EmbeddingService(settings)
    upload_service = UploadIngestionService(settings, repository, embeddings, max_upload_mb=settings.max_upload_mb)
    query_service = QueryService(settings, repository, embeddings)
    email_service = EmailIngestionService(
        repository=repository,
        email_client=EmailClient(settings),
        upload_service=upload_service,
        embedding_service=embeddings,
        query_service=query_service,
        poll_batch_size=settings.email_poll_batch_size,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        logger.info("Email worker shutdown signal received")
        stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows event loop may not support add_signal_handler for all signals.
            pass

    logger.info("Email worker started with poll interval %s seconds", settings.email_poll_interval_seconds)
    while not stop_event.is_set():
        try:
            result = await email_service.poll_and_process()
            logger.info("Email poll complete: processed=%s failed=%s", result["processed"], result["failed"])
        except Exception as exc:
            logger.exception("Email worker cycle failed: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(settings.email_poll_interval_seconds, 5))
        except TimeoutError:
            pass

    logger.info("Email worker exited gracefully")


def main() -> None:
    asyncio.run(run_email_worker_forever())


if __name__ == "__main__":
    main()
