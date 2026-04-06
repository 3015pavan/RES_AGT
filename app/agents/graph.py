from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    decide_tool_node,
    execute_sql_node,
    execute_vector_node,
    extract_intent_entities_node,
    format_response_node,
    merge_validate_node,
    normalize_query_node,
    plan_query_node,
)
from app.agents.state import AgentState
from app.core.config import Settings
from app.db.supabase_repo import SupabaseRepository
from app.services.embeddings import EmbeddingService


def build_graph(settings: Settings, repository: SupabaseRepository, embedding_service: EmbeddingService):
    graph = StateGraph(AgentState)

    graph.add_node("normalize_query", normalize_query_node(settings))
    graph.add_node("extract_intent", extract_intent_entities_node(settings))
    graph.add_node("plan", plan_query_node)
    graph.add_node("decide_tool", decide_tool_node)
    graph.add_node("execute_sql", execute_sql_node(repository))
    graph.add_node("execute_vector", execute_vector_node(repository, embedding_service))
    graph.add_node("validate", merge_validate_node)
    graph.add_node("respond", format_response_node(settings))

    graph.add_edge(START, "normalize_query")
    graph.add_edge("normalize_query", "extract_intent")
    graph.add_edge("extract_intent", "plan")
    graph.add_edge("plan", "decide_tool")

    def _tool_route(state: AgentState) -> str:
        choice = state.get("tool_choice", "none")
        if choice == "sql":
            return "sql"
        if choice == "vector":
            return "vector"
        if choice == "hybrid":
            return "hybrid"
        return "none"

    graph.add_conditional_edges(
        "decide_tool",
        _tool_route,
        {
            "sql": "execute_sql",
            "vector": "execute_vector",
            "hybrid": "execute_sql",
            "none": "validate",
        },
    )

    graph.add_edge("execute_sql", "execute_vector")
    graph.add_edge("execute_vector", "validate")
    graph.add_edge("validate", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
