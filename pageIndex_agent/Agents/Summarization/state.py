from typing import Optional
from typing_extensions import TypedDict


class SummarizationState(TypedDict):
    """State for the Summarization agent graph."""

    # Inputs
    user_request: str
    task_results: list  # list[{topic, pageindex_result, mcp_result}]

    # Output
    summary: str
    error: Optional[str]
