from __future__ import annotations

from io import BytesIO

import pandas as pd
from pypdf import PdfReader

SUPPORTED_MIME_TYPES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/pdf",
}


def parse_tabular(file_bytes: bytes, file_name: str) -> list[dict[str, str]]:
    lower = file_name.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(BytesIO(file_bytes))
    elif lower.endswith(".xlsx"):
        df = _read_excel_with_header_detection(file_bytes)
    else:
        raise ValueError("Unsupported tabular format")

    normalized = [{str(k).strip(): "" if pd.isna(v) else str(v).strip() for k, v in row.items()} for row in df.to_dict(orient="records")]
    return normalized


def _read_excel_with_header_detection(file_bytes: bytes) -> pd.DataFrame:
    # VTU-like sheets often include title rows before the actual table header.
    raw = pd.read_excel(BytesIO(file_bytes), header=None)

    header_idx = None
    max_scan = min(len(raw), 30)
    for idx in range(max_scan):
        row_values = [str(v).strip().lower() for v in raw.iloc[idx].tolist() if not pd.isna(v)]
        has_usn = any("usn" == value or "usn" in value for value in row_values)
        has_student = any("student" in value and "name" in value for value in row_values)
        if has_usn and has_student:
            header_idx = idx
            break

    if header_idx is None:
        # Fallback to default parser if no explicit header row is found.
        return pd.read_excel(BytesIO(file_bytes))

    header_row = raw.iloc[header_idx].tolist()
    columns = []
    for i, value in enumerate(header_row):
        name = str(value).strip() if not pd.isna(value) else f"col_{i}"
        if not name:
            name = f"col_{i}"
        columns.append(name)

    data = raw.iloc[header_idx + 1 :].copy()
    data.columns = columns
    data = data.dropna(how="all")
    return data


def parse_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(end - overlap, 0)
    return chunks
