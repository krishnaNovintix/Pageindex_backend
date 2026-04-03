from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import agentops
from agentops import start_trace, end_trace
from Agents.slack_agent.graph import build_graph
from Agents.slack_agent.logger import log_request, log_response, log_error, reset_log

router = APIRouter(prefix="/mcp-agent", tags=["mcp-agent"])


class AgentRequest(BaseModel):
    message: str
    thread_id: str = "default"


class AgentResponse(BaseModel):
    response: str


@router.post("/run", response_model=AgentResponse)
async def run_agent(body: AgentRequest):
    """
    Send a natural language message to the MCP agent.

    The agent uses tools exposed by the local MCP server to fulfil the request
    and returns the final response.

    Examples:
    - "List all users in my Notion workspace"
    - "Search Notion for pages about project planning"
    """
    trace = start_trace(trace_name="slack-agent-request", tags=["slack-agent", "request"])
    try:
        reset_log()
        log_request("mcp-agent/run", f"message={body.message!r} thread_id={body.thread_id!r}")

        graph = await build_graph()
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=body.message)]},
            config={"configurable": {"thread_id": body.thread_id}},
        )

        raw_content = result["messages"][-1].content
        # Gemini may return a list of content blocks instead of a plain string
        if isinstance(raw_content, list):
            response_text = " ".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in raw_content
            ).strip()
        else:
            response_text = raw_content or ""
        log_response("mcp-agent/run", f"response={response_text[:120]!r}")
        end_trace(trace_context=trace, end_state="Success")
        return JSONResponse(content={"response": response_text})

    except Exception as e:
        log_error("router/run", str(e))
        end_trace(trace_context=trace, end_state="Fail")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
