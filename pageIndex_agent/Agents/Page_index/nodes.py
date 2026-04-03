from agentops.sdk.decorators import operation
from Agents.Page_index.state import PageIndexState, IndexOutput, RetrieveOutput
from Agents.Page_index.utils import build_index_request, build_retrieve_request
from Agents.Page_index.logger import log_node_start, log_node_end, log_error


@operation(name="pageindex_index")
def call_index(state: PageIndexState) -> dict:
    """
    Node: Calls the PageIndex service to index a PDF and generate a structure JSON.
    """
    log_node_start("call_index")

    payload = build_index_request(
        pdf_path=state.index_input.pdf_path,
        output_dir=state.index_input.output_dir,
    )

    try:
        from Agents.pageindex_api.router import IndexRequest, index_document
        req = IndexRequest(pdf_path=payload["pdf_path"], output_dir=payload.get("output_dir", "results"))
        data = index_document(req)

        output = IndexOutput(
            success=True,
            structure_path=data.structure_path,
            message=data.message,
        )

        log_node_end("call_index", f"structure_path={output.structure_path}")
        return {"index_output": output}

    except Exception as e:
        log_error("call_index", str(e))
        return {"index_output": IndexOutput(success=False, message=str(e))}


@operation(name="pageindex_retrieve")
def call_retrieve(state: PageIndexState) -> dict:
    """
    Node: Calls the PageIndex service to retrieve relevant content for a query.
    """
    log_node_start("call_retrieve")

    payload = build_retrieve_request(
        pdf_path=state.retrieve_input.pdf_path,
        structure_path=state.retrieve_input.structure_path,
        query=state.retrieve_input.query,
        top_k=state.retrieve_input.top_k,
    )

    try:
        from Agents.pageindex_api.router import RetrieveRequest, retrieve
        req = RetrieveRequest(
            pdf_path=payload["pdf_path"],
            structure_path=payload["structure_path"],
            query=payload["query"],
            top_k=payload.get("top_k", 5),
        )
        data = retrieve(req)

        output = RetrieveOutput(
            query=data.query,
            nodes_used=data.nodes_used,
            node_titles=data.node_titles,
            thinking=data.thinking,
            answer=data.answer,
        )

        log_node_end("call_retrieve", f"nodes_used={output.nodes_used}")
        return {"retrieve_output": output}

    except Exception as e:
        log_error("call_retrieve", str(e))
        raise RuntimeError(f"Retrieval failed: {str(e)}")
