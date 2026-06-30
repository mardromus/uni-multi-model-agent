"""API request/response schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.models.domain import AgentResponse, ExecutionPlan, IntentType, ToolTraceEntry


class ChatMessage(BaseModel):
    role: str = "user"
    content: str = ""


class ChatRequest(BaseModel):
    message: str = ""
    session_id: str | None = None
    file_ids: list[str] = Field(default_factory=list)
    conversation_history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: AgentResponse
    session_id: str


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size_bytes: int


class AnalyzeRequest(BaseModel):
    message: str = ""
    file_ids: list[str] = Field(default_factory=list)
    stream: bool = False


class AnalyzeResponse(BaseModel):
    response: AgentResponse


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    tools_available: list[str] = Field(default_factory=list)


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class ToolsListResponse(BaseModel):
    tools: list[ToolInfo]


class TraceResponse(BaseModel):
    plan_id: str
    execution_plan: ExecutionPlan
    tool_trace: list[ToolTraceEntry]
    intent: IntentType | None = None
    final_answer: str = ""
    execution_time_ms: float = 0.0
