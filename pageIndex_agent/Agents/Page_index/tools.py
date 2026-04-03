import httpx
from langchain_core.tools import tool
from agentops.sdk.decorators import tool as agentops_tool
from Agents.Page_index.logger import log_node_start, log_node_end, log_error

PAGEINDEX_BASE_URL = "http://localhost:8001"


@agentops_tool(name="index_pdf")
@tool
def index_pdf(pdf_path: str, output_dir: str) -> str:
    """
    Index a PDF file and generate a structure JSON for later retrieval.

    Args:
        pdf_path: Absolute path to the PDF file to index.
        output_dir: Directory where the generated structure JSON will be saved.

    Returns:
        A message describing the result, including the path to the structure JSON on success.
    """
    log_node_start("tool:index_pdf")
    try:
        response = httpx.post(
            f"{PAGEINDEX_BASE_URL}/pageindex-api/index",
            json={"pdf_path": pdf_path, "output_dir": output_dir},
            timeout=3000.0,
        )
        response.raise_for_status()
        data = response.json()
        structure_path = data.get("structure_path", "unknown")
        message = data.get("message", "PDF indexed successfully")
        log_node_end("tool:index_pdf", f"structure_path={structure_path}")
        return f"{message} | structure_path={structure_path}"

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        log_error("tool:index_pdf", error_msg)
        return f"Indexing failed: {error_msg}"

    except Exception as e:
        log_error("tool:index_pdf", str(e))
        return f"Indexing failed: {str(e)}"


@agentops_tool(name="retrieve_from_pdf")
@tool
def retrieve_from_pdf(
    pdf_path: str,
    structure_path: str,
    query: str,
    top_k: int = 5,
) -> str:
    """
    Retrieve relevant content from an already-indexed PDF to answer a query.

    Args:
        pdf_path: Absolute path to the PDF file.
        structure_path: Path to the pre-built structure JSON (produced by index_pdf).
        query: Natural language question to answer from the PDF.
        top_k: Number of top nodes to retrieve (default: 5).

    Returns:
        The answer to the query along with the reasoning and matched section titles.
    """
    log_node_start("tool:retrieve_from_pdf")
    try:
        response = httpx.post(
            f"{PAGEINDEX_BASE_URL}/pageindex-api/retrieve",
            json={
                "pdf_path": pdf_path,
                "structure_path": structure_path,
                "query": query,
                "top_k": top_k,
            },
            timeout=1200.0,
        )
        response.raise_for_status()
        data = response.json()

        node_titles = ", ".join(data.get("node_titles", []))
        thinking = data.get("thinking", "")
        answer = data.get("answer", "")

        log_node_end("tool:retrieve_from_pdf", f"nodes_used={data.get('nodes_used')}")
        result = f"Sections used: {node_titles}\n"
        if thinking:
            result += f"Reasoning: {thinking}\n"
        result += f"Answer: {answer}"
        return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        log_error("tool:retrieve_from_pdf", error_msg)
        return f"Retrieval failed: {error_msg}"

    except Exception as e:
        log_error("tool:retrieve_from_pdf", str(e))
        return f"Retrieval failed: {str(e)}"
