from langgraph.graph import StateGraph, START, END

from Agents.Summarization.state import SummarizationState
from Agents.Summarization.nodes import summarize_node

_graph = None


def build_graph():
    """Build and cache the compiled Summarization LangGraph."""
    global _graph
    if _graph is not None:
        return _graph

    graph = StateGraph(SummarizationState)
    graph.add_node("summarize", summarize_node)
    graph.add_edge(START, "summarize")
    graph.add_edge("summarize", END)

    _graph = graph.compile()
    return _graph
