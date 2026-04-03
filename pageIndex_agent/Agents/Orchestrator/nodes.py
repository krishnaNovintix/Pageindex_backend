import json
import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from agentops.sdk.decorators import agent, operation, tool

from Agents.Orchestrator.state import OrchestratorState
from Agents.Orchestrator.prompt import PLAN_SYSTEM_PROMPT
from Agents.Orchestrator.logger import log_node_start, log_node_end, log_error


def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)


@agent(name="orchestrator")
class OrchestratorAgent:
    """AgentOps agent wrapper — each public method maps to an OPERATION span."""

    @operation(name="plan")
    async def plan(self, user_request: str, pdf_path: str) -> list:
        """Parse user intent into a list of TaskItems using an LLM."""
        llm = _get_llm()
        messages = [
            SystemMessage(content=PLAN_SYSTEM_PROMPT),
            HumanMessage(content=f"User request: {user_request}\nPDF path: {pdf_path}"),
        ]
        response = await llm.ainvoke(messages)
        content: str = response.content.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        tasks: list = []
        if start >= 0 and end > start:
            try:
                parsed = json.loads(content[start:end])
                tasks = parsed.get("tasks", [])
            except json.JSONDecodeError as exc:
                log_error("orchestrator:plan", f"JSON parse error: {exc} | raw={content[:300]}")
        return tasks

    @tool(name="retrieve_from_pageindex")
    async def retrieve(self, pdf_path: str, structure_path: str, topic: str) -> str:
        """Call the PageIndex retrieve function in-process to get content about a topic."""
        try:
            from Agents.pageindex_api.router import RetrieveRequest, retrieve as _retrieve_fn
            req = RetrieveRequest(
                pdf_path=pdf_path,
                structure_path=structure_path,
                query=topic,
                top_k=5,
            )
            # retrieve() is a sync function — call directly (FastAPI runs it in threadpool)
            import asyncio
            result = await asyncio.get_event_loop().run_in_executor(None, _retrieve_fn, req)
            node_titles = ", ".join(result.node_titles)
            out = f"Sections used: {node_titles}\n"
            if result.thinking:
                out += f"Reasoning: {result.thinking}\n"
            out += f"Answer: {result.answer}"
            return out
        except Exception as exc:
            log_error("orchestrator:retrieve", str(exc))
            return f"Retrieval failed: {exc}"

    @tool(name="call_summarization_agent")
    async def call_summarization(self, user_request: str, task_results: list) -> str:
        """Call the Summarization agent in-process to produce a coherent final answer."""
        try:
            from Agents.Summarization.graph import build_graph as build_summarization_graph
            graph = build_summarization_graph()
            # Coerce task_results entries to the expected dict shape
            coerced = [
                tr if isinstance(tr, dict) else {"topic": str(tr), "pageindex_result": "", "mcp_result": ""}
                for tr in task_results
            ]
            result = await graph.ainvoke(
                {
                    "user_request": user_request,
                    "task_results": coerced,
                    "summary": "",
                    "error": None,
                }
            )
            return result.get("summary", "")
        except Exception as exc:
            log_error("orchestrator:call_summarization", str(exc))
            return f"Summarization failed: {exc}"

    @tool(name="post_to_slack")
    async def post_to_slack(self, slack_instruction: str, content: str) -> str:
        """Call the Slack sub-agent in-process to post content to a channel."""
        message = f"{slack_instruction}\n\nContent to include:\n{content}"
        try:
            from Agents.slack_agent.graph import build_graph as build_slack_graph
            graph = await build_slack_graph()
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config={"configurable": {"thread_id": f"orch_{uuid.uuid4().hex}"}},
            )
            raw = result["messages"][-1].content
            if isinstance(raw, list):
                return " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in raw
                ).strip()
            return raw or ""
        except Exception as exc:
            log_error("orchestrator:post_to_slack", str(exc))
            return f"Slack action failed: {exc}"


# Singleton — created lazily so agentops.init() runs first
_orchestrator: OrchestratorAgent | None = None


def _get_orchestrator() -> OrchestratorAgent:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorAgent()
    return _orchestrator


# ---------------------------------------------------------------------------
# LangGraph node functions — thin wrappers around OrchestratorAgent methods
# ---------------------------------------------------------------------------

async def plan_node(state: OrchestratorState) -> dict:
    log_node_start("orchestrator:plan")
    tasks = await _get_orchestrator().plan(state["user_request"], state["pdf_path"])
    log_node_end("orchestrator:plan", f"tasks_count={len(tasks)}")
    return {
        "tasks": tasks,
        "current_task_index": 0,
        "task_results": [],
        "error": None,
    }


async def retrieve_node(state: OrchestratorState) -> dict:
    idx = state["current_task_index"]
    task = state["tasks"][idx]
    topic: str = task.get("topic", "")
    log_node_start(f"orchestrator:retrieve[{idx}]")

    pageindex_result = ""
    if task.get("needs_retrieval", True) and topic:
        pageindex_result = await _get_orchestrator().retrieve(
            state["pdf_path"], state["structure_path"], topic
        )
    else:
        log_node_end(f"orchestrator:retrieve[{idx}]", "skipped — needs_retrieval=False")

    log_node_end(f"orchestrator:retrieve[{idx}]", f"topic={topic!r}")
    updated_results = list(state.get("task_results", []))
    updated_results.append(
        {"topic": topic, "pageindex_result": pageindex_result, "mcp_result": ""}
    )
    return {"task_results": updated_results}


async def mcp_action_node(state: OrchestratorState) -> dict:
    idx = state["current_task_index"]
    task = state["tasks"][idx]
    result = state["task_results"][idx]
    log_node_start(f"orchestrator:mcp_action[{idx}]")

    mcp_result = ""
    if task.get("needs_slack", False):
        slack_instruction = task.get(
            "slack_instruction",
            f"Post the following content to the Slack channel with the title '{task.get('topic', 'Result')}'.",
        )
        mcp_result = await _get_orchestrator().post_to_slack(
            slack_instruction, result["pageindex_result"]
        )
    else:
        log_node_end(f"orchestrator:mcp_action[{idx}]", "skipped — needs_slack=False")

    log_node_end(f"orchestrator:mcp_action[{idx}]")
    updated_results = list(state["task_results"])
    updated_results[idx] = {**result, "mcp_result": mcp_result}
    return {
        "task_results": updated_results,
        "current_task_index": idx + 1,
    }


# ---------------------------------------------------------------------------
# Node: summarize
# ---------------------------------------------------------------------------

async def summarize_node(state: OrchestratorState) -> dict:
    """Call the Summarization agent to produce a clean, coherent final answer."""
    log_node_start("orchestrator:summarize")

    results: list = state.get("task_results", [])
    total = len(results)

    final_response = await _get_orchestrator().call_summarization(
        user_request=state["user_request"],
        task_results=results,
    )

    log_node_end("orchestrator:summarize", f"total_tasks={total}")
    return {"final_response": final_response}
