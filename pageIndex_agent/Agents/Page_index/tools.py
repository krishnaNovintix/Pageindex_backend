from langchain_core.tools import tool
from agentops.sdk.decorators import tool as agentops_tool
from Agents.Page_index.logger import log_node_start, log_node_end, log_error


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
        from Agents.pageindex_api.router import IndexRequest, index_document
        req = IndexRequest(pdf_path=pdf_path, output_dir=output_dir)
        data = index_document(req)
        log_node_end("tool:index_pdf", f"structure_path={data.structure_path}")
        return f"{data.message} | structure_path={data.structure_path}"
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
        from Agents.pageindex_api.router import RetrieveRequest, retrieve
        req = RetrieveRequest(pdf_path=pdf_path, structure_path=structure_path, query=query, top_k=top_k)
        data = retrieve(req)
        node_titles = ", ".join(data.node_titles)
        log_node_end("tool:retrieve_from_pdf", f"nodes_used={data.nodes_used}")
        result = f"Sections used: {node_titles}\n"
        if data.thinking:
            result += f"Reasoning: {data.thinking}\n"
        result += f"Answer: {data.answer}"
        return result
    except Exception as e:
        log_error("tool:retrieve_from_pdf", str(e))
        return f"Retrieval failed: {str(e)}"
