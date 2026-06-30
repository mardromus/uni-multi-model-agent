"""Domain models for the agent application."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class InputType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"
    AUDIO = "audio"
    MIXED = "mixed"


class IntentType(str, Enum):
    GENERAL_QUESTION = "general_question"
    SUMMARY = "summary"
    OCR = "ocr"
    TRANSCRIPTION = "transcription"
    CODE_EXPLANATION = "code_explanation"
    SENTIMENT = "sentiment"
    COMPARISON = "comparison"
    CROSS_INPUT_REASONING = "cross_input_reasoning"
    ACTION_ITEM_EXTRACTION = "action_item_extraction"
    YOUTUBE_SUMMARY = "youtube_summary"


class ToolStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProcessedInput(BaseModel):
    """Normalized input after parsing."""

    text: str | None = None
    file_paths: list[str] = Field(default_factory=list)
    file_types: list[str] = Field(default_factory=list)
    youtube_urls: list[str] = Field(default_factory=list)
    input_type: InputType = InputType.TEXT
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntentResult(BaseModel):
    """Result of intent detection."""

    intent: IntentType
    confidence: float
    reasoning: str = ""
    requires_clarification: bool = False
    clarification_question: str | None = None


class PlanStep(BaseModel):
    """Single step in execution plan."""

    step_number: int
    tool_name: str
    description: str
    status: ToolStatus = ToolStatus.PENDING
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0


class ExecutionPlan(BaseModel):
    """Full execution plan with trace."""

    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    steps: list[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_tokens: int = 0
    estimated_cost_usd: float = 0.0


class ToolTraceEntry(BaseModel):
    """Individual tool execution trace."""

    tool_name: str
    status: ToolStatus
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    error: str | None = None


class AgentResponse(BaseModel):
    """Final agent response."""

    response_id: str = Field(default_factory=lambda: str(uuid4()))
    extracted_text: str = ""
    final_answer: str = ""
    reasoning_steps: list[str] = Field(default_factory=list)
    tool_trace: list[ToolTraceEntry] = Field(default_factory=list)
    execution_plan: ExecutionPlan | None = None
    execution_time_ms: float = 0.0
    clarification_question: str | None = None
    token_estimate: int = 0
    cost_estimate_usd: float = 0.0
    needs_clarification: bool = False
