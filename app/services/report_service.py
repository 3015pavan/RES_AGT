from __future__ import annotations

from typing import Any

from app.db.supabase_repo import SupabaseRepository
from app.models.schemas import NO_DATA_MESSAGE, ReportType


class ReportService:
    def __init__(self, repository: SupabaseRepository) -> None:
        self.repository = repository

    def generate(
        self,
        report_type: ReportType,
        filters: dict[str, Any],
        grade_scale: dict[str, float] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | str:
        payload = {"filters": filters, "grade_scale": grade_scale or {}}
        if report_type is ReportType.student:
            rows = self.repository.run_safe_sql("student_report", payload)
        elif report_type is ReportType.class_report:
            rows = self.repository.run_safe_sql("class_report", payload)
        elif report_type is ReportType.subject:
            rows = self.repository.run_safe_sql("subject_report", payload)
        else:
            rows = []

        return rows if rows else NO_DATA_MESSAGE
