from __future__ import annotations

import re
from typing import Any

import httpx
from tenacity import Retrying, stop_after_attempt, wait_exponential

from app.agents.state import AgentState
from app.core.config import Settings
from app.core.resilience import CircuitBreaker
from app.db.supabase_repo import SupabaseRepository
from app.models.schemas import NO_DATA_MESSAGE
from app.services.embeddings import EmbeddingService

_grok_circuit = CircuitBreaker()

_SUBJECT_CODE_HINTS = {
    "cs11": "data structures",
    "cs12": "database management systems",
    "cs13": "operating systems",
    "cs14": "computer networks",
    "hs15": "machine learning",
}


def _extract_subject_from_text(text: str) -> tuple[str | None, str | None]:
    code_name_match = re.search(r"\b([a-z]{2}\d{2})\s*[\-\u2013]\s*([a-z][a-z\s]+)", text, re.IGNORECASE)
    if code_name_match:
        return code_name_match.group(1).upper(), code_name_match.group(2).strip().lower()

    code_match = re.search(r"\b([a-z]{2}\d{2})\b", text, re.IGNORECASE)
    if code_match:
        code = code_match.group(1).lower()
        return code.upper(), _SUBJECT_CODE_HINTS.get(code)

    lower = text.lower()
    for code, subject_name in _SUBJECT_CODE_HINTS.items():
        if subject_name in lower:
            return code.upper(), subject_name

    return None, None


def _extract_grade_from_text(text: str) -> str | None:
    grade_match = re.search(r"\b(?:grade|got|scored|with)\s*(A\+|B\+|A|B|C|P|F)(?![A-Za-z0-9\+])", text, re.IGNORECASE)
    if not grade_match:
        grade_match = re.search(r"(?<![A-Za-z0-9])(A\+|B\+|A|B|C|P|F)(?![A-Za-z0-9\+])", text, re.IGNORECASE)
    if not grade_match:
        return None
    return grade_match.group(1).upper()


def _extract_student_name_from_text(text: str) -> str | None:
    # Handles forms like: Student_10, student 10, or student-10.
    student_match = re.search(r"\b(student(?:[_\-\s]+[a-z0-9]+))\b", text, re.IGNORECASE)
    if not student_match:
        return None
    raw = student_match.group(1).strip()
    normalized = re.sub(r"[_\-\s]+", "_", raw).lower()
    if normalized in {"student_details", "student_information", "student_info", "student_performance"}:
        return None

    suffix = normalized.replace("student_", "", 1)
    if re.fullmatch(r"[1-9][a-z]{2}\d{2}[a-z]{2}\d{3}", suffix):
        return None

    return normalized.title()


def _deterministic_response(state: AgentState) -> str | None:
    rows = state.get("sql_result_rows", [])
    if not rows:
        return None

    intent = state.get("intent")
    entities = state.get("entities", {})

    if intent == "student_lookup":
        first = rows[0]
        lines = [
            "Student Information:",
            f"- USN: {first.get('usn', 'N/A')}",
            f"- Student Name: {first.get('student_name', 'N/A')}",
            "",
            "Subject-wise Performance:",
        ]
        for idx, row in enumerate(rows, start=1):
            subject_label = f"{row.get('subject_code', '')} - {row.get('subject_name', '')}".strip(" -")
            lines.extend(
                [
                    f"{idx}. {subject_label}",
                    f"   - Marks: {row.get('marks', 'N/A')}/{row.get('max_marks', 'N/A')}",
                    f"   - Grade: {row.get('grade', 'N/A')}",
                    f"   - Pass/Fail: {row.get('pass_fail', 'N/A')}",
                ]
            )
        return "\n".join(lines)

    if intent == "report_generation" and entities.get("grade"):
        grade = entities.get("grade")
        subject = entities.get("subject") or entities.get("subject_code") or "requested subject"
        lines = [f"Students with grade {grade} in {subject}:"]
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"{idx}. {row.get('usn', 'N/A')} - {row.get('student_name', 'N/A')} (Grade: {row.get('grade', 'N/A')}, Marks: {row.get('marks', 'N/A')})"
            )
        return "\n".join(lines)

    if intent == "ranking":
        lines = ["Ranking Results:"]
        for idx, row in enumerate(rows, start=1):
            rank_value = row.get("rank_position", idx)
            lines.append(
                f"{rank_value}. {row.get('usn', 'N/A')} - {row.get('student_name', 'N/A')} (Total: {row.get('total_marks', 'N/A')}, Average: {row.get('average_marks', 'N/A')})"
            )
        return "\n".join(lines)

    if intent == "aggregation":
        lines = ["Student Aggregates:"]
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"{idx}. {row.get('usn', 'N/A')} - {row.get('student_name', 'N/A')} (Total: {row.get('total_marks', 'N/A')}, Average: {row.get('average_marks', 'N/A')})"
            )
        return "\n".join(lines)

    if intent == "subject_analysis":
        lines = ["Subject Analysis:"]
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"{idx}. {row.get('subject_name', 'N/A')} (Highest: {row.get('highest', 'N/A')}, Lowest: {row.get('lowest', 'N/A')}, Average: {row.get('average', 'N/A')})"
            )
        return "\n".join(lines)

    if intent == "comparison":
        lines = ["Comparison Against Class Average:"]
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"{idx}. {row.get('subject_name', 'N/A')}: {row.get('usn', 'N/A')} ({row.get('student_name', 'N/A')}) Marks {row.get('marks', 'N/A')}, Class Avg {row.get('class_average', 'N/A')}, Delta {row.get('delta_from_average', 'N/A')}"
            )
        return "\n".join(lines)

    if intent == "report_generation":
        lines = ["Report Results:"]
        for idx, row in enumerate(rows, start=1):
            subject = row.get("subject_name", "N/A")
            grade = row.get("grade", "N/A")
            marks = row.get("marks", "N/A")
            lines.append(
                f"{idx}. {row.get('usn', 'N/A')} - {row.get('student_name', 'N/A')} | {subject} | Grade: {grade} | Marks: {marks}"
            )
        return "\n".join(lines)

    return None


def _call_grok(settings: Settings, prompt: str) -> str:
    _grok_circuit.failure_threshold = max(settings.circuit_failure_threshold, 1)
    _grok_circuit.recovery_seconds = max(settings.circuit_recovery_seconds, 1)
    if not _grok_circuit.allow():
        raise RuntimeError("Grok circuit breaker open")

    # LLM integration is scoped to normalization/extraction/formatting only.
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.llm_model_name,
        "messages": [{"role": "system", "content": "Return concise structured text only."}, {"role": "user", "content": prompt}],
        "temperature": 0,
    }
    retrying = Retrying(
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(max(settings.grok_max_retries, 1)),
        reraise=True,
    )
    with httpx.Client(timeout=settings.external_call_timeout_seconds) as client:
        try:
            for attempt in retrying:
                with attempt:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
            _grok_circuit.record_success()
        except Exception:
            _grok_circuit.record_failure()
            raise
    return data["choices"][0]["message"]["content"].strip()


def normalize_query_node(settings: Settings):
    def _node(state: AgentState) -> AgentState:
        raw = state.get("raw_query", "").strip()
        if not raw:
            return {**state, "normalized_query": ""}

        prompt = (
            "Normalize this user query into clear canonical form without adding facts. "
            f"Query: {raw}"
        )
        try:
            normalized = _call_grok(settings, prompt)
        except Exception:
            normalized = raw
        return {**state, "normalized_query": normalized}

    return _node


def extract_intent_entities_node(settings: Settings):
    def _node(state: AgentState) -> AgentState:
        raw_text = state.get("raw_query", "")
        text = state.get("normalized_query", "") or raw_text
        parse_text = f"{raw_text} {text}".strip()
        prompt = (
            "Classify intent from [student_lookup, subject_analysis, ranking, comparison, aggregation, report_generation]. "
            "Extract entities as JSON-like text with keys usn, subject, semester, filters. "
            "If critical fields are missing, include missing_fields list. Query: "
            f"{text}"
        )
        try:
            extracted = _call_grok(settings, prompt)
        except Exception:
            extracted = ""

        # Deterministic fallback parsing to avoid schema ambiguity from model text output.
        lower = parse_text.lower()
        intent = "student_lookup"
        grade = _extract_grade_from_text(parse_text)
        subject_code, subject_name = _extract_subject_from_text(parse_text)
        student_name = _extract_student_name_from_text(parse_text)

        if any(token in lower for token in ["list all students", "students who", "who got", "which students"]):
            intent = "report_generation"
        elif "top" in lower or "rank" in lower:
            intent = "ranking"
        elif "average" in lower or "lowest" in lower or "highest" in lower:
            intent = "subject_analysis"
        elif "report" in lower:
            intent = "report_generation"
        elif "compare" in lower:
            intent = "comparison"
        elif "sgpa" in lower or "aggregate" in lower:
            intent = "aggregation"

        entities: dict[str, Any] = {"raw_extraction": extracted}
        usn_match = re.search(r"\b[1-9][A-Za-z]{2}\d{2}[A-Za-z]{2}\d{3}\b", parse_text)
        if usn_match:
            entities["usn"] = usn_match.group(0).upper()

        # Grade+subject queries are class/filter requests and must not require USN.
        if grade and (subject_name or subject_code) and "usn" not in entities:
            intent = "report_generation"

        if student_name:
            entities["student_name"] = student_name

        if grade:
            entities["grade"] = grade

        if subject_code:
            entities["subject_code"] = subject_code
        if subject_name:
            entities["subject"] = subject_name

        semester_match = re.search(r"\b(?:sem|semester)\s*(\d+)\b", lower)
        if semester_match:
            entities["semester"] = int(semester_match.group(1))

        subject_aliases = {
            "phy": "physics",
            "physics": "physics",
            "chem": "chemistry",
            "chemistry": "chemistry",
            "math": "mathematics",
            "mathematics": "mathematics",
        }
        detected_subject = None
        for token in re.findall(r"[a-zA-Z]+", lower):
            if token in subject_aliases:
                detected_subject = subject_aliases[token]
                break
        if detected_subject:
            entities["subject"] = detected_subject

        scope_tokens = {"class", "overall", "all", "batch"}
        if any(token in lower for token in scope_tokens):
            entities["scope"] = "class"

        missing_fields: list[str] = []

        if intent == "student_lookup" and "usn" not in entities and "student_name" not in entities:
            missing_fields.append("usn_or_student_name")
        if intent in {"subject_analysis", "ranking"} and "subject" not in entities and entities.get("scope") != "class":
            if intent == "ranking" and entities.get("semester") is not None:
                pass
            else:
                missing_fields.append("subject_or_scope")

        if missing_fields:
            return {
                **state,
                "intent": "clarification",
                "entities": entities,
                "missing_fields": missing_fields,
                "clarification_question": f"Please provide: {', '.join(missing_fields)}",
            }

        return {**state, "intent": intent, "entities": entities, "missing_fields": []}

    return _node


def plan_query_node(state: AgentState) -> AgentState:
    if state.get("intent") == "clarification":
        return {**state, "tool_choice": "none", "tool_plan": {"kind": "clarification"}}

    intent = state.get("intent", "student_lookup")
    entities = state.get("entities", {})
    if intent in {"student_lookup", "aggregation", "ranking", "comparison", "subject_analysis", "report_generation"}:
        if intent == "report_generation" and (entities.get("subject") or entities.get("subject_code") or entities.get("grade")):
            plan = {"sql_rpc": "student_lookup", "vector_needed": False}
        else:
            plan = {"sql_rpc": intent, "vector_needed": intent in {"subject_analysis", "report_generation"}}
    else:
        plan = {"sql_rpc": "student_lookup", "vector_needed": False}
    return {**state, "tool_plan": plan}


def decide_tool_node(state: AgentState) -> AgentState:
    if state.get("intent") == "clarification":
        return {**state, "tool_choice": "none"}

    plan = state.get("tool_plan", {})
    vector_needed = bool(plan.get("vector_needed"))
    sql_needed = bool(plan.get("sql_rpc"))

    if sql_needed and vector_needed:
        choice = "hybrid"
    elif sql_needed:
        choice = "sql"
    elif vector_needed:
        choice = "vector"
    else:
        choice = "none"

    return {**state, "tool_choice": choice}


def execute_sql_node(repository: SupabaseRepository):
    def _node(state: AgentState) -> AgentState:
        if state.get("tool_choice") not in {"sql", "hybrid"}:
            return state

        rpc_name = state.get("tool_plan", {}).get("sql_rpc", "student_lookup")
        entities = state.get("entities", {})
        resolved_usn = entities.get("usn")

        if not resolved_usn and entities.get("student_name"):
            expected_name = str(entities["student_name"]).strip().lower()
            matches = [
                s
                for s in repository.list_students(limit=500)
                if str(s.get("student_name") or "").strip().lower() == expected_name
            ]
            if len(matches) == 1:
                resolved_usn = matches[0].get("usn")
            elif len(matches) > 1:
                return {
                    **state,
                    "intent": "clarification",
                    "missing_fields": ["usn"],
                    "clarification_question": f"Multiple students found for {entities['student_name']}. Please provide: usn",
                    "sql_result_rows": [],
                }

        params = {
            "usn": resolved_usn,
            "subject": entities.get("subject"),
            "semester": entities.get("semester"),
            "filters": entities.get("filters", {}),
            "normalized_query": state.get("normalized_query", ""),
        }
        rows = repository.run_safe_sql(rpc_name, params)

        grade_filter = entities.get("grade")
        if grade_filter:
            rows = [row for row in rows if str(row.get("grade") or "").upper() == str(grade_filter).upper()]

        subject_code_filter = entities.get("subject_code")
        if subject_code_filter:
            rows = [row for row in rows if str(row.get("subject_code") or "").upper() == str(subject_code_filter).upper()]

        if entities.get("student_name") and not resolved_usn:
            expected_name = str(entities["student_name"]).strip().lower()
            rows = [row for row in rows if str(row.get("student_name") or "").strip().lower() == expected_name]

        return {**state, "sql_result_rows": rows}

    return _node


def execute_vector_node(repository: SupabaseRepository, embedding_service: EmbeddingService):
    def _node(state: AgentState) -> AgentState:
        if state.get("tool_choice") not in {"vector", "hybrid"}:
            return state

        normalized_query = state.get("normalized_query") or state.get("raw_query", "")
        if not normalized_query:
            return {**state, "vector_result_chunks": []}

        query_embedding = embedding_service.embed_text(normalized_query)
        chunks = repository.search_vector_chunks(query_embedding, limit=5)
        return {**state, "vector_result_chunks": chunks}

    return _node


def merge_validate_node(state: AgentState) -> AgentState:
    if state.get("intent") == "clarification":
        question = state.get("clarification_question", "Please provide required details.")
        return {**state, "validation_status": "ok", "merged_result": {"clarification": question}}

    sql_rows = state.get("sql_result_rows", [])
    vector_chunks = state.get("vector_result_chunks", [])
    merged = {"sql": sql_rows, "vector": vector_chunks}

    if not sql_rows and not vector_chunks:
        return {**state, "merged_result": merged, "validation_status": "no_data", "final_response": NO_DATA_MESSAGE}

    return {**state, "merged_result": merged, "validation_status": "ok"}


def format_response_node(settings: Settings):
    def _node(state: AgentState) -> AgentState:
        if state.get("final_response") == NO_DATA_MESSAGE:
            return state

        if state.get("intent") == "clarification":
            question = state.get("merged_result", {}).get("clarification", "Please provide more details.")
            return {**state, "final_response": question}

        deterministic = _deterministic_response(state)
        if deterministic:
            return {**state, "final_response": deterministic}

        merged = state.get("merged_result", {})
        prompt = (
            "Format the following retrieved data into a concise, clear response. "
            "Do not add any facts beyond provided data. "
            f"Data: {merged}"
        )
        try:
            formatted = _call_grok(settings, prompt)
        except Exception:
            formatted = str(merged)
        if not formatted.strip():
            formatted = NO_DATA_MESSAGE
        return {**state, "final_response": formatted}

    return _node
