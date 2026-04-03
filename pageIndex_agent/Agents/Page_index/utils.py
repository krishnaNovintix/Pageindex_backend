def build_index_request(pdf_path: str, output_dir: str) -> dict:
    """
    Builds the payload dict for the /index endpoint.
    """
    return {
        "pdf_path": pdf_path,
        "output_dir": output_dir,
    }


def build_retrieve_request(
    pdf_path: str,
    structure_path: str,
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Builds the payload dict for the /retrieve endpoint.
    """
    return {
        "pdf_path": pdf_path,
        "structure_path": structure_path,
        "query": query,
        "top_k": top_k,
    }
