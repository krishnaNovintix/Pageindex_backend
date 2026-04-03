import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from agentops.sdk.decorators import agent, operation
from Agents.slack_agent.state import ChatState
from Agents.slack_agent.tools import slack_send_message, slack_list_channels, slack_ping
from Agents.slack_agent.logger import log_node_start, log_node_end

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_graph = None

SLACK_TOOLS = [slack_send_message, slack_list_channels, slack_ping]


def _get_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
    )


@agent(name="slack_agent")
class _SlackAgentGraph:
    """Thin wrapper so AgentOps tracks the Slack agent's chat node as an AGENT span."""

    @operation(name="slack_chat_node")
    async def chat(self, llm_with_tools, messages):
        return await llm_with_tools.ainvoke(messages)


_slack_agent_instance: _SlackAgentGraph | None = None


def _get_slack_agent() -> _SlackAgentGraph:
    global _slack_agent_instance
    if _slack_agent_instance is None:
        _slack_agent_instance = _SlackAgentGraph()
    return _slack_agent_instance


async def build_graph():
    """Build and cache the compiled LangGraph chatbot with direct Slack tools."""
    global _graph
    if _graph is not None:
        return _graph

    llm_with_tools = _get_llm().bind_tools(SLACK_TOOLS)

    async def chat_node(state: ChatState):
        log_node_start("chat_node")
        messages = state["messages"]
        response = await _get_slack_agent().chat(llm_with_tools, messages)
        log_node_end("chat_node", f"finish_reason={getattr(response, 'response_metadata', {}).get('finish_reason', 'unknown')}")
        return {"messages": [response]}

    tool_node = ToolNode(SLACK_TOOLS)

    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "chat_node")
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
    graph.add_edge("chat_node", END)

    memory = MemorySaver()
    _graph = graph.compile(checkpointer=memory)
    return _graph
