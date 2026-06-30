"""API route handlers."""

import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.agents.orchestrator import AgentOrchestrator
from app.api.dependencies import (
    get_agent_orchestrator,
    get_file_service_dep,
    get_settings_dep,
    get_tool_registry_dep,
    get_trace_service_dep,
)
from app.config.settings import Settings
from app.schemas.api import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ToolInfo,
    ToolsListResponse,
    TraceResponse,
    UploadResponse,
)
from app.services.file_service import FileService
from app.services.trace_service import TraceService
from app.tools.base import ToolRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    registry: ToolRegistry = Depends(get_tool_registry_dep),
    settings: Settings = Depends(get_settings_dep),
) -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        tools_available=registry.list_names(),
    )


@router.get("/tools", response_model=ToolsListResponse)
async def list_tools(
    registry: ToolRegistry = Depends(get_tool_registry_dep),
) -> ToolsListResponse:
    """List all available tools with schemas."""
    tools = [
        ToolInfo(
            name=t.name,
            description=t.description,
            input_schema=t.input_schema(),
            output_schema=t.output_schema(),
        )
        for t in registry.list_tools()
    ]
    return ToolsListResponse(tools=tools)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_service: FileService = Depends(get_file_service_dep),
    settings: Settings = Depends(get_settings_dep),
) -> UploadResponse:
    """Upload a file for analysis."""
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_size_mb}MB limit",
        )

    try:
        meta = await file_service.save_file(
            filename=file.filename or "unknown",
            content=content,
            content_type=file.content_type,
        )
        return UploadResponse(
            file_id=meta["file_id"],
            filename=meta["filename"],
            content_type=meta["content_type"],
            size_bytes=meta["size_bytes"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> ChatResponse:
    """Process a chat message with optional file references."""
    history = [{"role": m.role, "content": m.content} for m in request.conversation_history]
    response, session_id = await agent.run(
        text=request.message,
        file_ids=request.file_ids,
        conversation_history=history,
        session_id=request.session_id,
    )
    return ChatResponse(response=response, session_id=session_id)


@router.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    agent: AgentOrchestrator = Depends(get_agent_orchestrator),
):
    """Analyze inputs with optional streaming."""
    if request.stream:

        async def event_generator():
            async for event in agent.run_stream(
                text=request.message, file_ids=request.file_ids
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    response, _ = await agent.run(text=request.message, file_ids=request.file_ids)
    return AnalyzeResponse(response=response)


@router.get("/trace/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    trace_service: TraceService = Depends(get_trace_service_dep),
) -> TraceResponse:
    """Retrieve execution trace by ID."""
    response = trace_service.get_trace(trace_id)
    if not response:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    from app.models.domain import ExecutionPlan

    plan = response.execution_plan or ExecutionPlan()

    return TraceResponse(
        plan_id=trace_id,
        execution_plan=plan,
        tool_trace=response.tool_trace,
        final_answer=response.final_answer,
        execution_time_ms=response.execution_time_ms,
    )
