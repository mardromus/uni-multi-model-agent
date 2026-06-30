"""LangGraph workflow definition."""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    clarification_node,
    input_parser_node,
    intent_detector_node,
    output_formatter_node,
    planning_node,
    tool_executor_node,
)
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


def should_clarify(state: AgentState) -> Literal["clarify", "plan"]:
    """Route based on clarification need."""
    if state.get("needs_clarification"):
        return "clarify"
    return "plan"


def build_agent_graph():
    """Build and compile the LangGraph agent workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("input_parser", input_parser_node)
    workflow.add_node("intent_detector", intent_detector_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("output_formatter", output_formatter_node)

    # Define edges
    workflow.set_entry_point("input_parser")
    workflow.add_edge("input_parser", "intent_detector")
    workflow.add_conditional_edges(
        "intent_detector",
        should_clarify,
        {"clarify": "clarification", "plan": "planning"},
    )
    workflow.add_edge("clarification", "output_formatter")
    workflow.add_edge("planning", "tool_executor")
    workflow.add_edge("tool_executor", "output_formatter")
    workflow.add_edge("output_formatter", END)

    return workflow.compile()


_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
