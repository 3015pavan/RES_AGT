from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration


REQUIRED_ENV = [
    "INTEGRATION_API_BASE_URL",
]


def _require_env() -> None:
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        pytest.skip(f"Missing env for integration tests: {missing}")


def _api_url(path: str) -> str:
    base = os.environ["INTEGRATION_API_BASE_URL"].rstrip("/")
    return f"{base}{path}"


def test_upload_real_file_if_provided() -> None:
    _require_env()
    upload_file_path = os.getenv("INTEGRATION_UPLOAD_FILE")
    if not upload_file_path:
        pytest.skip("Set INTEGRATION_UPLOAD_FILE to run upload test")

    path = Path(upload_file_path)
    if not path.exists():
        pytest.skip(f"Upload file not found: {path}")

    with path.open("rb") as f:
        files = {"file": (path.name, f, "application/octet-stream")}
        response = httpx.post(_api_url("/upload"), files=files, timeout=120)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["documents_created"] >= 1


def test_chat_query_real_data_or_no_data() -> None:
    _require_env()
    query = os.getenv("INTEGRATION_CHAT_QUERY", "sgpa 1MS21CS001")
    response = httpx.post(_api_url("/chat"), json={"query": query}, timeout=120)

    assert response.status_code == 200
    body = response.json()
    assert "response" in body
    assert isinstance(body["response"], str)


def test_report_student_real_data_or_no_data() -> None:
    _require_env()
    usn = os.getenv("INTEGRATION_REPORT_USN")
    payload = {
        "report_type": "student",
        "filters": {"usn": usn} if usn else {},
    }
    response = httpx.post(_api_url("/report"), json=payload, timeout=120)

    assert response.status_code == 200
    body = response.json()
    assert body["report_type"] == "student"


def test_no_data_behavior_exact_message() -> None:
    _require_env()
    impossible_usn = "ZZ99ZZ999"
    response = httpx.post(_api_url("/chat"), json={"query": f"marks of {impossible_usn}"}, timeout=120)

    assert response.status_code == 200
    body = response.json()
    # System contract requires exact message if retrieval is empty.
    assert body["response"] == "NO DATA AVAILABLE"


def test_email_poll_trigger() -> None:
    _require_env()
    if os.getenv("INTEGRATION_ENABLE_EMAIL_TEST", "0") != "1":
        pytest.skip("Set INTEGRATION_ENABLE_EMAIL_TEST=1 to run email poll test")

    response = httpx.post(_api_url("/email/poll"), timeout=180)
    assert response.status_code == 200
    body = response.json()
    assert "processed" in body
    assert "failed" in body
