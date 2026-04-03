"""
PageIndex core API endpoints — /index and /retrieve.
These are included directly in the agent server so only one process is needed.

sys.path is patched here (before any pageindex imports) so the pageindex
package at the repo root is importable regardless of which directory the
server is launched from.
"""

import os
import sys
import json
from pathlib import Path

# ── Make the repo root (parent of pageIndex_agent/) importable ────────────────
_REPO_ROOT = Path(__file__).resolve().parents[3]   # .../PageIndex
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import agentops
from agentops import TraceState
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import PyPDF2
import pageIndex_agent.pageindex.utils as pi_utils
from pageIndex_agent.pageindex.page_index import page_index_main
from pageIndex_agent.pageindex.utils import ConfigLoader

# resolve_stored_path lives in backend_python/utils.py which is on sys.path
from utils import resolve_stored_path

_DOCS_DIR = str(Path(__file__).resolve().parents[2] / "backend_python" / "documents")

router = APIRouter(prefix="/pageindex-api", tags=["pageindex-api"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class IndexRequest(BaseModel):
    pdf_path: str
    output_dir: str = "results"


class IndexResponse(BaseModel):
    doc_name: str
    structure_path: str
    node_count: int
    message: str


class RetrieveRequest(BaseModel):
    pdf_path: str
    structure_path: str
    query: str
    top_k: int = 5


class RetrieveResponse(BaseModel):
    query: str
    nodes_used: list[str]
    node_titles: list[str]
    thinking: str
    answer: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_nodes(tree: list) -> int:
    count = 0
    for node in tree:
        count += 1
        if node.get("nodes"):
            count += _count_nodes(node["nodes"])
    return count


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/index", response_model=IndexResponse, summary="Index a PDF → tree structure JSON")
def index_document(req: IndexRequest):
    """
    Index a PDF file and save its hierarchical tree structure to a JSON file.

    - **pdf_path**: absolute path to the PDF file
    - **output_dir**: directory where the structure JSON will be saved (default: `results/`)
    """
    pdf_path = resolve_stored_path(req.pdf_path, fallback_dir=_DOCS_DIR)
    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")
    if not pdf_path.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported on this endpoint.")

    opt = ConfigLoader().load(None)

    _trace = agentops.start_trace(
        trace_name="pdf_indexing",
        tags=["indexing", "pdf", Path(pdf_path).name],
    )
    try:
        result = page_index_main(pdf_path, opt)
    except Exception as e:
        agentops.end_trace(_trace, end_state=TraceState.ERROR)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")

    output_dir = Path(req.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_stem = Path(pdf_path).stem
    output_path = output_dir / f"{pdf_stem}_structure.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    node_count = _count_nodes(result.get("structure", []))

    agentops.end_trace(_trace, end_state=TraceState.SUCCESS)
    return IndexResponse(
        doc_name=result.get("doc_name", pdf_stem),
        structure_path=str(output_path),
        node_count=node_count,
        message=f"Indexed successfully. Structure saved to {output_path}",
    )


@router.post("/retrieve", response_model=RetrieveResponse, summary="Query an indexed document")
def retrieve(req: RetrieveRequest):
    """
    Perform reasoning-based retrieval from an already-indexed document.

    - **pdf_path**: path to the original PDF file
    - **structure_path**: path to the structure JSON saved by `/pageindex-api/index`
    - **query**: natural language question
    - **top_k**: max number of nodes to fetch content from (default: 5)
    """
    pdf_path = resolve_stored_path(req.pdf_path, fallback_dir=_DOCS_DIR)
    structure_path = os.path.abspath(req.structure_path)

    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")
    if not os.path.isfile(structure_path):
        raise HTTPException(status_code=404, detail=f"Structure JSON not found: {structure_path}")

    with open(structure_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tree = data.get("structure", data)

    opt = ConfigLoader().load(None)
    retrieve_model = getattr(opt, "retrieve_model", None) or opt.model
    answer_model = opt.model

    _trace = agentops.start_trace(
        trace_name="document_retrieval",
        tags=["retrieval", "pdf", Path(pdf_path).name],
    )

    # ── Step 1: Select relevant nodes from the tree ───────────────────────────
    tree_no_text = pi_utils.remove_fields(tree, fields=["text"])
    search_prompt = f"""You are given a question and a document tree (each node has node_id, title, summary).
Your job: return a JSON object listing the node_ids most likely to contain the answer.

Reply with ONLY valid JSON, no extra text:
{{
  "thinking": "<brief reasoning>",
  "node_list": ["node_id1", "node_id2"]
}}

Question: {req.query}

Document tree:
{json.dumps(tree_no_text, indent=2)[:20000]}
"""
    resp = pi_utils.llm_completion(model=retrieve_model, prompt=search_prompt)
    resp_json = pi_utils.extract_json(resp)
    node_list = resp_json.get("node_list") or []
    thinking = resp_json.get("thinking", "")

    if not node_list:
        agentops.end_trace(_trace, end_state=TraceState.ERROR)
        raise HTTPException(
            status_code=422,
            detail=f"Model returned no nodes. Raw response: {resp[:500]}",
        )

    # ── Step 2: Extract page content for selected nodes ───────────────────────
    node_map = pi_utils.create_node_mapping(tree)
    reader = PyPDF2.PdfReader(pdf_path)
    contexts: list[str] = []
    node_titles: list[str] = []

    for nid in node_list[: req.top_k]:
        node = node_map.get(nid)
        if not node:
            continue
        start = node.get("start_index")
        end = node.get("end_index", start)
        title = node.get("title", "?")
        node_titles.append(title)
        if not start:
            continue
        for pg in range(start, end + 1):
            try:
                text = reader.pages[pg - 1].extract_text() or ""
                if text.strip():
                    contexts.append(f"--- Page {pg} ({title}) ---\n{text}")
            except IndexError:
                continue

    if not contexts:
        agentops.end_trace(_trace, end_state=TraceState.ERROR)
        raise HTTPException(
            status_code=422,
            detail="No page content could be extracted for the selected nodes.",
        )

    context = "\n\n".join(contexts)[:20000]

    # ── Step 3: Generate answer ───────────────────────────────────────────────
    final_prompt = f"""Using ONLY the context below, answer the question clearly and concisely.
Cite the page number and section title when relevant.

Context:
{context}

Question: {req.query}
"""
    answer = pi_utils.llm_completion(model=answer_model, prompt=final_prompt)

    agentops.end_trace(_trace, end_state=TraceState.SUCCESS)
    return RetrieveResponse(
        query=req.query,
        nodes_used=node_list[: req.top_k],
        node_titles=node_titles,
        thinking=thinking,
        answer=answer,
    )
