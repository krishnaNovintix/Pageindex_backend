from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from agentops.sdk.decorators import agent, operation

from Agents.Summarization.state import SummarizationState
from Agents.Summarization.prompt import SUMMARIZE_SYSTEM_PROMPT
from Agents.Summarization.logger import log_node_start, log_node_end, log_error


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.2)


def _build_user_message(user_request: str, task_results: list) -> str:
    """Format all retrieved results into a single LLM user message."""
    lines = [f"User's original request: {user_request}\n"]

    has_slack = any(r.get("mcp_result") for r in task_results)

    for i, result in enumerate(task_results, 1):
        topic = result.get("topic") or f"Task {i}"
        pageindex_result = result.get("pageindex_result", "").strip()
        mcp_result = result.get("mcp_result", "").strip()

        lines.append(f"--- Retrieved excerpt {i}: {topic} ---")
        if pageindex_result:
            lines.append(pageindex_result)
        else:
            lines.append("(No content retrieved for this topic.)")

        if mcp_result:
            lines.append(f"[Slack action taken: {mcp_result[:120]}]")
        lines.append("")

    if has_slack:
        lines.append("Note: One or more results were also posted to Slack as requested.")

    return "\n".join(lines)


@agent(name="summarization_agent")
class SummarizationAgent:
    """AgentOps agent wrapper for the Summarization agent."""

    @operation(name="summarize")
    async def summarize(self, user_request: str, task_results: list) -> str:
        """Call the LLM to produce a coherent summary from all task results."""
        llm = _get_llm()
        user_message = _build_user_message(user_request, task_results)
        messages = [
            SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
        response = await llm.ainvoke(messages)
        return response.content.strip()


_summarization_agent: SummarizationAgent | None = None


def _get_summarization_agent() -> SummarizationAgent:
    global _summarization_agent
    if _summarization_agent is None:
        _summarization_agent = SummarizationAgent()
    return _summarization_agent


# ---------------------------------------------------------------------------
# LangGraph node function
# ---------------------------------------------------------------------------

async def summarize_node(state: SummarizationState) -> dict:
    log_node_start("summarization:summarize")
    try:
        summary = await _get_summarization_agent().summarize(
            state["user_request"],
            state["task_results"],
        )
        log_node_end("summarization:summarize", f"summary_length={len(summary)}")
        return {"summary": summary, "error": None}
    except Exception as exc:
        log_error("summarization:summarize", str(exc))
        return {"summary": "", "error": str(exc)}
