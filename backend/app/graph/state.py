"""LangGraph agent state definition."""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages

from app.models.domain import (
    AgentResponse,
    ExecutionPlan,
    IntentResult,
    PlanStep,
    ProcessedInput,
    ToolTraceEntry,
)


class AgentState(TypedDict, total=False):
    """State passed through LangGraph nodes."""

    # Input
    processed_input: ProcessedInput
    conversation_history: list[dict[str, str]]

    # Intent
    intent_result: IntentResult

    # Planning
    execution_plan: ExecutionPlan
    plan_steps: list[PlanStep]
    reasoning_steps: list[str]

    # Execution
    tool_outputs: list[dict[str, Any]]
    tool_trace: list[ToolTraceEntry]
    extracted_texts: list[str]

    # Output
    final_answer: str
    extracted_text: str
    agent_response: AgentResponse

    # Control
    needs_clarification: bool
    clarification_question: str | None
    error: str | None
    start_time_ms: float
    messages: Annotated[list, add_messages]
