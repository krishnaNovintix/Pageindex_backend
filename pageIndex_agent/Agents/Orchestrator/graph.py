from langgraph.graph import StateGraph, START, END

from Agents.Orchestrator.state import OrchestratorState
from Agents.Orchestrator.nodes import (
    plan_node,
    retrieve_node,
    mcp_action_node,
    summarize_node,
)

_graph = None


# ---------------------------------------------------------------------------
# Conditional edge helpers
# ---------------------------------------------------------------------------

def _after_plan(state: OrchestratorState) -> str:
    """Route to retrieve if there are tasks, else skip straight to summarize."""
    if state.get("tasks"):
        return "retrieve"
    return "summarize"


def _after_mcp_action(state: OrchestratorState) -> str:
    """Loop back to retrieve while tasks remain; otherwise summarize."""
    if state["current_task_index"] < len(state["tasks"]):
        return "retrieve"
    return "summarize"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph():
    """Build and cache the compiled orchestrator LangGraph."""
    global _graph
    if _graph is not None:
        return _graph

    graph = StateGraph(OrchestratorState)

    graph.add_node("plan", plan_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("mcp_action", mcp_action_node)
    graph.add_node("summarize", summarize_node)

    graph.add_edge(START, "plan")

    graph.add_conditional_edges(
        "plan",
        _after_plan,
        {"retrieve": "retrieve", "summarize": "summarize"},
    )

    graph.add_edge("retrieve", "mcp_action")

    graph.add_conditional_edges(
        "mcp_action",
        _after_mcp_action,
        {"retrieve": "retrieve", "summarize": "summarize"},
    )

    graph.add_edge("summarize", END)

    _graph = graph.compile()
    return _graph
