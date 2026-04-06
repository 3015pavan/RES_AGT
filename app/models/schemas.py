from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field

NO_DATA_MESSAGE = "NO DATA AVAILABLE"


class SourceType(str, Enum):
    upload = "upload"
    email = "email"


class UploadResponse(BaseModel):
    rows_ingested: int
    documents_created: int
    document_ids: list[str] = Field(default_factory=list)
    status: str


class ErrorItem(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorItem


class NormalizedResultRow(BaseModel):
    usn: str
    student_name: str | None = None
    semester: int | None = None
    section: str | None = None
    subject_code: str
    subject_name: str
    credits: float | None = None
    exam_type: str | None = None
    marks: float | None = None
    max_marks: float | None = None
    grade: str | None = None
    pass_fail: str | None = None


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: str
    intent: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)


class ReportType(str, Enum):
    student = "student"
    class_report = "class"
    subject = "subject"


class ReportRequest(BaseModel):
    report_type: ReportType
    filters: dict[str, Any] = Field(default_factory=dict)
    grade_scale: dict[str, float] | None = None


class ReportResponse(BaseModel):
    report_type: ReportType
    data: dict[str, Any] | list[dict[str, Any]] | str


class PollResponse(BaseModel):
    processed: int
    failed: int


class StudentsListResponse(BaseModel):
    data: list[dict[str, Any]]


class DocumentsListResponse(BaseModel):
    data: list[dict[str, Any]]


class EmailQueryRequest(BaseModel):
    sender_email: EmailStr
    query: str
