"""FastAPI dependency injection."""

from functools import lru_cache

from app.agents.orchestrator import AgentOrchestrator
from app.config.settings import Settings, get_settings
from app.services.file_service import FileService, get_file_service
from app.services.input_processor import InputProcessor
from app.services.trace_service import TraceService, get_trace_service
from app.tools.base import ToolRegistry, get_tool_registry


@lru_cache
def get_agent_orchestrator() -> AgentOrchestrator:
    file_service = get_file_service()
    return AgentOrchestrator(
        input_processor=InputProcessor(file_service),
        trace_service=get_trace_service(),
        tool_registry=get_tool_registry(),
    )


def get_settings_dep() -> Settings:
    return get_settings()


def get_file_service_dep() -> FileService:
    return get_file_service()


def get_trace_service_dep() -> TraceService:
    return get_trace_service()


def get_tool_registry_dep() -> ToolRegistry:
    return get_tool_registry()
