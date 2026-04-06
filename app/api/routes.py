from __future__ import annotations

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import require_scopes
from app.db.supabase_repo import SupabaseRepository
from app.models.schemas import (
    NO_DATA_MESSAGE,
    ChatRequest,
    ChatResponse,
    DocumentsListResponse,
    ErrorEnvelope,
    PollResponse,
    ReportRequest,
    ReportResponse,
    StudentsListResponse,
    UploadResponse,
)
from app.services.email_client import EmailClient
from app.services.email_ingestion import EmailIngestionService
from app.services.embeddings import EmbeddingService
from app.services.query_service import QueryService
from app.services.report_service import ReportService
from app.services.upload_ingestion import UploadIngestionService

router = APIRouter()


def get_repository(settings: Settings = Depends(get_settings)) -> SupabaseRepository:
    return SupabaseRepository(settings)


def get_embedding_service(settings: Settings = Depends(get_settings)) -> EmbeddingService:
    return EmbeddingService(settings)


def get_upload_service(
    settings: Settings = Depends(get_settings),
    repository: SupabaseRepository = Depends(get_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> UploadIngestionService:
    return UploadIngestionService(settings, repository, embedding_service, max_upload_mb=settings.max_upload_mb)


def get_query_service(
    settings: Settings = Depends(get_settings),
    repository: SupabaseRepository = Depends(get_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> QueryService:
    return QueryService(settings, repository, embedding_service)


def get_email_service(
    settings: Settings = Depends(get_settings),
    repository: SupabaseRepository = Depends(get_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    upload_service: UploadIngestionService = Depends(get_upload_service),
    query_service: QueryService = Depends(get_query_service),
) -> EmailIngestionService:
    return EmailIngestionService(
        repository=repository,
        email_client=EmailClient(settings),
        upload_service=upload_service,
        embedding_service=embedding_service,
        query_service=query_service,
        poll_batch_size=settings.email_poll_batch_size,
    )


COMMON_ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope, "description": "Unauthorized"},
    403: {"model": ErrorEnvelope, "description": "Forbidden"},
    413: {"model": ErrorEnvelope, "description": "Payload too large"},
    415: {"model": ErrorEnvelope, "description": "Unsupported media type"},
    429: {"model": ErrorEnvelope, "description": "Rate limited"},
}


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload and ingest document",
    tags=["ingestion"],
    responses=COMMON_ERROR_RESPONSES,
)
async def upload_file(
    file: UploadFile = File(...),
    _api_key: str = Depends(require_scopes(["ingest:upload"])),
    service: UploadIngestionService = Depends(get_upload_service),
):
    if not file.filename:
        raise AppError(code="BAD_REQUEST", message="File name is required", status_code=400)

    if file.content_type is None:
        raise AppError(code="BAD_REQUEST", message="Missing file content type", status_code=400)

    result = await service.ingest(file)
    return UploadResponse(**result)


@router.post(
    "/email/poll",
    response_model=PollResponse,
    summary="Poll unread emails and ingest",
    tags=["ingestion"],
    responses=COMMON_ERROR_RESPONSES,
)
async def poll_email(
    settings: Settings = Depends(get_settings),
    _api_key: str = Depends(require_scopes(["ingest:email"])),
    service: EmailIngestionService = Depends(get_email_service),
):
    if not settings.email_automation_enabled:
        raise AppError(code="EMAIL_AUTOMATION_DISABLED", message="Email automation is disabled", status_code=503)
    result = await service.poll_and_process()
    return PollResponse(**result)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Run grounded chat query",
    tags=["query"],
    responses=COMMON_ERROR_RESPONSES,
)
async def chat_query(
    payload: ChatRequest = Body(
        ...,
        examples=[
            {"query": "marks phy of 1MS21CS002"},
            {"query": "who top in sem 5"},
        ],
    ),
    _api_key: str = Depends(require_scopes(["query:chat"])),
    service: QueryService = Depends(get_query_service),
):
    result = service.ask(payload.query)
    final_response = result.get("final_response", NO_DATA_MESSAGE)
    return ChatResponse(
        response=final_response,
        intent=result.get("intent"),
        entities=result.get("entities", {}),
    )


@router.get("/students", response_model=StudentsListResponse, tags=["catalog"], responses=COMMON_ERROR_RESPONSES)
def list_students(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _api_key: str = Depends(require_scopes(["read:students"])),
    repository: SupabaseRepository = Depends(get_repository),
) -> StudentsListResponse:
    return {"data": repository.list_students(limit=limit, offset=offset)}


@router.get("/documents", response_model=DocumentsListResponse, tags=["catalog"], responses=COMMON_ERROR_RESPONSES)
def list_documents(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _api_key: str = Depends(require_scopes(["read:documents"])),
    repository: SupabaseRepository = Depends(get_repository),
) -> DocumentsListResponse:
    return {"data": repository.list_documents(limit=limit, offset=offset)}


@router.post(
    "/report",
    response_model=ReportResponse,
    summary="Generate SQL-grounded report",
    tags=["query"],
    responses=COMMON_ERROR_RESPONSES,
)
def generate_report(
    payload: ReportRequest = Body(
        ...,
        examples=[
            {"report_type": "student", "filters": {"usn": "1MS21CS001"}},
            {"report_type": "subject", "filters": {"subject": "physics"}},
        ],
    ),
    _api_key: str = Depends(require_scopes(["report:generate"])),
    repository: SupabaseRepository = Depends(get_repository),
):
    service = ReportService(repository)
    data = service.generate(payload.report_type, payload.filters, payload.grade_scale)
    return ReportResponse(report_type=payload.report_type, data=data)
