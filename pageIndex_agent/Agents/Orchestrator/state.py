from typing import Optional
from typing_extensions import TypedDict


class TaskItem(TypedDict):
    """A single task produced by the planner."""
    topic: str                  # Query sent to the PageIndex agent (empty if not needed)
    slack_instruction: str      # Instruction sent to the Slack agent (empty if not needed)
    needs_retrieval: bool       # Whether to call the PageIndex agent
    needs_slack: bool           # Whether to call the Slack agent


class TaskResult(TypedDict):
    """Collected output for one task after both agents have run."""
    topic: str
    pageindex_result: str
    mcp_result: str


class OrchestratorState(TypedDict):
    # Inputs
    user_request: str
    pdf_path: str
    structure_path: str

    # Planning output
    tasks: list            # list[TaskItem]

    # Execution tracking
    current_task_index: int
    task_results: list     # list[TaskResult]

    # Final output
    final_response: str
    error: Optional[str]
