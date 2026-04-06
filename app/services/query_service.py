from __future__ import annotations

from typing import Literal

from app.agents.graph import build_graph
from app.agents.state import AgentState
from app.core.config import Settings
from app.db.supabase_repo import SupabaseRepository
from app.models.schemas import NO_DATA_MESSAGE
from app.services.embeddings import EmbeddingService


class QueryService:
    def __init__(self, settings: Settings, repository: SupabaseRepository, embedding_service: EmbeddingService) -> None:
        self.settings = settings
        self.repository = repository
        self.embedding_service = embedding_service
        self.graph = build_graph(settings=settings, repository=repository, embedding_service=embedding_service)

    def ask(self, query: str, channel: Literal["chat", "email"] = "chat") -> AgentState:
        state: AgentState = {"raw_query": query}
        result = self.graph.invoke(state)
        if not result.get("final_response"):
            result["final_response"] = NO_DATA_MESSAGE

        try:
            self.repository.insert_query_log(
                {
                    "channel": channel,
                    "raw_query": query,
                    "normalized_query": result.get("normalized_query"),
                    "intent": result.get("intent"),
                    "tool_choice": result.get("tool_choice"),
                    "sql_result_count": len(result.get("sql_result_rows", [])),
                    "vector_result_count": len(result.get("vector_result_chunks", [])),
                    "final_response": result.get("final_response"),
                    "status": result.get("validation_status", "unknown"),
                    "metadata": {
                        "missing_fields": result.get("missing_fields", []),
                        "tool_plan": result.get("tool_plan", {}),
                    },
                }
            )
        except Exception:
            # Audit persistence must never break user-facing query execution.
            pass

        return result
