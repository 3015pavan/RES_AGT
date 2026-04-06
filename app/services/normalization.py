from __future__ import annotations

import re
from typing import Any

from app.models.schemas import NormalizedResultRow

_COLUMN_ALIASES = {
    "usn": ["usn", "student_usn", "regno", "registration_no", "registration number"],
    "student_name": ["student_name", "name", "student", "student name"],
    "semester": ["semester", "sem", "term"],
    "section": ["section", "sec"],
    "subject_code": ["subject_code", "subject code", "code", "sub_code"],
    "subject_name": ["subject_name", "subject", "subject name", "course"],
    "credits": ["credits", "credit"],
    "exam_type": ["exam_type", "exam", "assessment", "test"],
    "marks": ["marks", "score", "obtained", "obtained_marks"],
    "max_marks": ["max_marks", "total", "out_of", "max"],
    "grade": ["grade", "letter_grade"],
    "pass_fail": ["pass_fail", "result", "status"],
}


def _canonical_key(raw_key: str) -> str:
    lowered = raw_key.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return lowered


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    f = _to_float(value)
    if f is None:
        return None
    return int(f)


def _resolve_value(record: dict[str, Any], canonical_name: str) -> Any:
    for alias in _COLUMN_ALIASES[canonical_name]:
        key = _canonical_key(alias)
        if key in record:
            return record[key]
    return None


def _is_valid_usn(usn: str) -> bool:
    # VTU-style USN examples: 1MS22CS001
    return bool(re.fullmatch(r"[1-9][A-Z]{2}\d{2}[A-Z]{2}\d{3}", usn))


def _normalize_subject_name(raw_name: str) -> str:
    clean = raw_name.replace("_", " ").strip()
    return re.sub(r"\s+", " ", clean).title()


def _extract_wide_subject_rows(
    canonical_record: dict[str, Any],
    usn: str,
    student_name: str | None,
    semester: int | None,
    section: str | None,
    pass_fail: str | None,
) -> list[NormalizedResultRow]:
    # Wide VTU sheet columns often look like:
    # cs11_data_structures_gr, cs11_data_structures_gp, ...
    pattern = re.compile(r"^([a-z]{2}\d{2})_(.+)_(gr|gp)$")
    combined_pattern = re.compile(r"^([a-z]{2}\d{2})_(.+)_gr_gp$")
    subjects: dict[str, dict[str, Any]] = {}

    for key, value in canonical_record.items():
        match = pattern.match(key)
        if match:
            code = match.group(1).upper()
            subject_name = _normalize_subject_name(match.group(2))
            metric = match.group(3)

            if code not in subjects:
                subjects[code] = {"subject_name": subject_name, "gr": None, "gp": None}

            if metric == "gr":
                subjects[code]["gr"] = str(value).strip().upper() if value is not None and str(value).strip() else None
            elif metric == "gp":
                subjects[code]["gp"] = _to_float(value)
            continue

        combined_match = combined_pattern.match(key)
        if not combined_match:
            continue

        code = combined_match.group(1).upper()
        subject_name = _normalize_subject_name(combined_match.group(2))

        if code not in subjects:
            subjects[code] = {"subject_name": subject_name, "gr": None, "gp": None}

        cell = "" if value is None else str(value).strip()
        if not cell:
            continue

        # Expected values like A/9 or A+ / 10.
        if "/" in cell:
            left, right = cell.split("/", maxsplit=1)
            grade = left.strip().upper() if left.strip() else None
            gp = _to_float(right.strip())
            subjects[code]["gr"] = grade
            subjects[code]["gp"] = gp
        else:
            # Fallback: parse numeric as gp, otherwise parse as grade.
            gp = _to_float(cell)
            if gp is not None:
                subjects[code]["gp"] = gp
            else:
                subjects[code]["gr"] = cell.upper()

    rows: list[NormalizedResultRow] = []
    for code, data in subjects.items():
        if data.get("gr") is None and data.get("gp") is None:
            continue
        rows.append(
            NormalizedResultRow(
                usn=usn,
                student_name=student_name,
                semester=semester,
                section=section,
                subject_code=code,
                subject_name=data["subject_name"],
                exam_type="semester",
                marks=data.get("gp"),
                max_marks=10.0 if data.get("gp") is not None else None,
                grade=data.get("gr"),
                pass_fail=pass_fail,
            )
        )

    return rows


def extract_student_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    students: list[dict[str, Any]] = []
    seen_usn: set[str] = set()

    for original in records:
        canonical_record = {_canonical_key(k): v for k, v in original.items()}
        usn_raw = _resolve_value(canonical_record, "usn")
        if not usn_raw:
            continue

        usn = str(usn_raw).strip().upper()
        if not _is_valid_usn(usn):
            continue
        if not usn or usn in seen_usn:
            continue

        seen_usn.add(usn)
        students.append(
            {
                "usn": usn,
                "student_name": (str(_resolve_value(canonical_record, "student_name")).strip() if _resolve_value(canonical_record, "student_name") else None),
                "semester": _to_int(_resolve_value(canonical_record, "semester")),
                "section": (str(_resolve_value(canonical_record, "section")).strip() if _resolve_value(canonical_record, "section") else None),
            }
        )

    return students


def normalize_result_records(records: list[dict[str, Any]]) -> list[NormalizedResultRow]:
    normalized_rows: list[NormalizedResultRow] = []

    for original in records:
        canonical_record = {_canonical_key(k): v for k, v in original.items()}

        usn_raw = _resolve_value(canonical_record, "usn")
        subject_name_raw = _resolve_value(canonical_record, "subject_name")
        subject_code_raw = _resolve_value(canonical_record, "subject_code")

        if not usn_raw:
            continue

        usn = str(usn_raw).strip().upper()
        if not _is_valid_usn(usn):
            continue

        student_name = (str(_resolve_value(canonical_record, "student_name")).strip() if _resolve_value(canonical_record, "student_name") else None)
        semester = _to_int(_resolve_value(canonical_record, "semester"))
        section = (str(_resolve_value(canonical_record, "section")).strip() if _resolve_value(canonical_record, "section") else None)
        pass_fail = (str(_resolve_value(canonical_record, "pass_fail")).strip().upper() if _resolve_value(canonical_record, "pass_fail") else None)

        if not subject_name_raw and not subject_code_raw:
            wide_rows = _extract_wide_subject_rows(
                canonical_record=canonical_record,
                usn=usn,
                student_name=student_name,
                semester=semester,
                section=section,
                pass_fail=pass_fail,
            )
            normalized_rows.extend(wide_rows)
            continue

        subject_name = str(subject_name_raw).strip() if subject_name_raw else str(subject_code_raw).strip()
        subject_code = str(subject_code_raw).strip().upper() if subject_code_raw else subject_name[:12].upper().replace(" ", "_")

        row = NormalizedResultRow(
            usn=usn,
            student_name=student_name,
            semester=semester,
            section=section,
            subject_code=subject_code,
            subject_name=subject_name,
            credits=_to_float(_resolve_value(canonical_record, "credits")),
            exam_type=(str(_resolve_value(canonical_record, "exam_type")).strip() if _resolve_value(canonical_record, "exam_type") else None),
            marks=_to_float(_resolve_value(canonical_record, "marks")),
            max_marks=_to_float(_resolve_value(canonical_record, "max_marks")),
            grade=(str(_resolve_value(canonical_record, "grade")).strip().upper() if _resolve_value(canonical_record, "grade") else None),
            pass_fail=pass_fail,
        )
        normalized_rows.append(row)

    return normalized_rows
