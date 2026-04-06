from typing import Any, Literal, TypedDict

IntentType = Literal[
    "student_lookup",
    "subject_analysis",
    "ranking",
    "comparison",
    "aggregation",
    "report_generation",
    "clarification",
]

ToolType = Literal["sql", "vector", "hybrid", "none"]


class AgentState(TypedDict, total=False):
    raw_query: str
    normalized_query: str
    intent: IntentType
    entities: dict[str, Any]
    missing_fields: list[str]
    clarification_question: str
    tool_plan: dict[str, Any]
    tool_choice: ToolType
    sql_result_rows: list[dict[str, Any]]
    vector_result_chunks: list[dict[str, Any]]
    merged_result: dict[str, Any]
    validation_status: Literal["ok", "no_data", "error"]
    final_response: str
