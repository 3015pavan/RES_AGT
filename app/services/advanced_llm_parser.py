from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import httpx

from app.core.config import Settings
from app.models.schemas import NormalizedResultRow


class AdvancedLLMParser:
    """LLM-assisted parser for heterogeneous datasets.

    This parser never fabricates source text. It only transforms provided records/text into
    normalized row objects that can then be validated and stored.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def parse_document_with_llamaparse(self, file_bytes: bytes, file_name: str) -> str | None:
        """Parse documents using official LlamaParse SDK when configured.

        Returns parsed text/markdown or None when LlamaParse is unavailable.
        """
        api_key = (self.settings.llama_cloud_api_key or "").strip()
        if not api_key:
            return None

        try:
            from llama_parse import LlamaParse  # type: ignore[import-not-found]
        except Exception:
            return None

        suffix = os.path.splitext(file_name)[1] or ".bin"
        result_type = (self.settings.llama_parse_result_type or "markdown").strip().lower()
        if result_type not in {"markdown", "text"}:
            result_type = "markdown"

        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name

            parser = LlamaParse(api_key=api_key, result_type=result_type)
            docs = parser.load_data(temp_path)
            chunks: list[str] = []
            for doc in docs or []:
                text = getattr(doc, "text", None)
                if text and str(text).strip():
                    chunks.append(str(text).strip())

            merged = "\n\n".join(chunks).strip()
            return merged or None
        except Exception:
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def parse_records(self, records: list[dict[str, Any]]) -> list[NormalizedResultRow]:
        if not self.settings.llm_parser_enabled or not records:
            return []

        compact_records = records[:80]
        result_type = (self.settings.llama_parse_result_type or "markdown").strip().lower()
        if result_type == "markdown":
            input_payload = self._records_to_markdown(compact_records)
            input_label = "Markdown table"
        else:
            input_payload = json.dumps(compact_records, ensure_ascii=True)
            input_label = "JSON records"

        prompt = (
            "Convert these tabular records into JSON array rows for academic results. "
            "Return only JSON array. For each row use keys: "
            "usn, student_name, semester, section, subject_code, subject_name, marks, max_marks, grade, pass_fail. "
            "Do not invent values; skip uncertain fields by setting null. "
            f"Input format: {input_label}. "
            f"Records: {input_payload}"
        )
        return self._call_and_parse(prompt)

    def parse_text(self, text: str) -> list[NormalizedResultRow]:
        if not self.settings.llm_parser_enabled or not text.strip():
            return []

        snippet = text[:15000]
        result_type = (self.settings.llama_parse_result_type or "markdown").strip().lower()
        prompt = (
            "Extract academic result rows from this text and return only JSON array. "
            "Use keys: usn, student_name, semester, section, subject_code, subject_name, marks, max_marks, grade, pass_fail. "
            "Do not invent values; only extract what exists in text. "
            f"Expected source parse type: {result_type}. "
            f"Text: {snippet}"
        )
        return self._call_and_parse(prompt)

    def _call_and_parse(self, prompt: str) -> list[NormalizedResultRow]:
        url = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.llm_model_name,
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }

        try:
            with httpx.Client(timeout=self.settings.external_call_timeout_seconds) as client:
                res = client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                content = res.json()["choices"][0]["message"]["content"]
        except Exception:
            return []

        normalized_json = self._extract_json_array(content)
        if normalized_json is None:
            return []

        rows: list[NormalizedResultRow] = []
        for item in normalized_json:
            if not isinstance(item, dict):
                continue
            usn = str(item.get("usn", "")).strip().upper()
            subject_code = item.get("subject_code")
            subject_name = item.get("subject_name")
            if not usn or (not subject_code and not subject_name):
                continue

            rows.append(
                NormalizedResultRow(
                    usn=usn,
                    student_name=self._to_str(item.get("student_name")),
                    semester=self._to_int(item.get("semester")),
                    section=self._to_str(item.get("section")),
                    subject_code=str(subject_code).strip().upper() if subject_code else str(subject_name).strip().upper().replace(" ", "_")[:12],
                    subject_name=str(subject_name).strip() if subject_name else str(subject_code).strip(),
                    marks=self._to_float(item.get("marks")),
                    max_marks=self._to_float(item.get("max_marks")),
                    grade=self._to_str(item.get("grade"), upper=True),
                    pass_fail=self._to_str(item.get("pass_fail"), upper=True),
                )
            )

        return rows

    @staticmethod
    def _extract_json_array(content: str) -> list[Any] | None:
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()

        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            start = content.find("[")
            end = content.rfind("]")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                parsed = json.loads(content[start : end + 1])
                return parsed if isinstance(parsed, list) else None
            except json.JSONDecodeError:
                return None

    @staticmethod
    def _to_str(value: Any, upper: bool = False) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text.upper() if upper else text

    @staticmethod
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

    @staticmethod
    def _to_int(value: Any) -> int | None:
        f = AdvancedLLMParser._to_float(value)
        if f is None:
            return None
        return int(f)

    @staticmethod
    def _records_to_markdown(records: list[dict[str, Any]]) -> str:
        if not records:
            return ""

        keys: list[str] = []
        seen: set[str] = set()
        for row in records:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)

        header = "| " + " | ".join(keys) + " |"
        separator = "| " + " | ".join(["---"] * len(keys)) + " |"
        lines = [header, separator]

        for row in records:
            values: list[str] = []
            for key in keys:
                value = row.get(key)
                if value is None:
                    values.append("")
                else:
                    text = str(value).replace("\n", " ").replace("|", "\\|").strip()
                    values.append(text)
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)
