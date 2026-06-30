"""Trace storage service for execution plans."""

import json
import logging
from pathlib import Path

from app.config.settings import Settings, get_settings
from app.models.domain import AgentResponse, ExecutionPlan

logger = logging.getLogger(__name__)


class TraceService:
    """Store and retrieve execution traces."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.trace_dir = self.settings.trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, AgentResponse] = {}

    def save_trace(self, response: AgentResponse) -> str:
        """Persist trace to disk and memory."""
        plan_id = (
            response.execution_plan.plan_id
            if response.execution_plan
            else response.response_id
        )
        self._memory[plan_id] = response

        trace_path = self.trace_dir / f"{plan_id}.json"
        try:
            trace_path.write_text(response.model_dump_json(indent=2))
        except Exception as e:
            logger.warning("Failed to persist trace to disk: %s", e)

        return plan_id

    def get_trace(self, trace_id: str) -> AgentResponse | None:
        if trace_id in self._memory:
            return self._memory[trace_id]

        trace_path = self.trace_dir / f"{trace_id}.json"
        if trace_path.exists():
            try:
                data = json.loads(trace_path.read_text())
                response = AgentResponse.model_validate(data)
                self._memory[trace_id] = response
                return response
            except Exception as e:
                logger.error("Failed to load trace %s: %s", trace_id, e)
        return None


_trace_service: TraceService | None = None


def get_trace_service() -> TraceService:
    global _trace_service
    if _trace_service is None:
        _trace_service = TraceService()
    return _trace_service
