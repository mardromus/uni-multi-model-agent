"""Main agent orchestrator."""

import logging
import time
import uuid
from typing import Any

from app.graph.workflow import get_agent_graph
from app.models.domain import AgentResponse, ProcessedInput
from app.services.input_processor import InputProcessor
from app.services.trace_service import TraceService, get_trace_service
from app.tools.base import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates the full agent pipeline."""

    def __init__(
        self,
        input_processor: InputProcessor,
        trace_service: TraceService,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.input_processor = input_processor
        self.trace_service = trace_service
        self.tool_registry = tool_registry or get_tool_registry()
        self.graph = get_agent_graph()

    async def run(
        self,
        text: str = "",
        file_ids: list[str] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        session_id: str | None = None,
    ) -> tuple[AgentResponse, str]:
        """Execute the full agent pipeline."""
        session_id = session_id or str(uuid.uuid4())
        start = time.time()

        processed = await self.input_processor.process(text=text, file_ids=file_ids)

        initial_state: dict[str, Any] = {
            "processed_input": processed,
            "conversation_history": conversation_history or [],
            "tool_outputs": [],
            "tool_trace": [],
            "extracted_texts": [],
            "reasoning_steps": [],
            "_tool_registry": self.tool_registry,
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            response: AgentResponse = result.get("agent_response")

            if not response:
                response = AgentResponse(
                    final_answer="An unexpected error occurred.",
                    execution_time_ms=(time.time() - start) * 1000,
                )

            self.trace_service.save_trace(response)
            logger.info(
                "Agent completed in %.0fms, session=%s",
                response.execution_time_ms,
                session_id,
            )
            return response, session_id

        except Exception as e:
            logger.exception("Agent pipeline failed")
            response = AgentResponse(
                final_answer=f"I encountered an error processing your request: {e!s}",
                reasoning_steps=[f"Pipeline error: {e!s}"],
                execution_time_ms=(time.time() - start) * 1000,
            )
            return response, session_id

    async def run_stream(
        self,
        text: str = "",
        file_ids: list[str] | None = None,
        session_id: str | None = None,
    ):
        """Stream agent execution events."""
        session_id = session_id or str(uuid.uuid4())

        yield {"event": "start", "session_id": session_id}

        processed = await self.input_processor.process(text=text, file_ids=file_ids)
        yield {"event": "input_processed", "input_type": processed.input_type.value}

        response, sid = await self.run(
            text=text, file_ids=file_ids, session_id=session_id
        )

        if response.execution_plan:
            for step in response.execution_plan.steps:
                yield {
                    "event": "plan_step",
                    "step": step.model_dump(),
                }

        for trace in response.tool_trace:
            yield {"event": "tool_trace", "trace": trace.model_dump()}

        yield {
            "event": "complete",
            "response": response.model_dump(),
            "session_id": sid,
        }
