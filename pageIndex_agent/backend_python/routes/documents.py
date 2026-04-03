"""
/api/documents routes

GET    /                   — list all documents (sorted newest first)
POST   /upload             — upload a PDF file, store it, register in DB
GET    /{doc_id}           — get one document by id
POST   /                   — register a document by path (backward compat)
PUT    /{doc_id}           — update a document
DELETE /{doc_id}           — delete a document record
POST   /{doc_id}/mark-indexed — mark a document as indexed
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, UploadFile, File
from pymongo import ReturnDocument

from database import get_db
from utils import serialize_doc

router = APIRouter()

# ── Storage directories ───────────────────────────────────────────────────────
# Defaults sit inside backend_python/ itself; override via env vars for hosting.
_BASE = Path(__file__).resolve().parent.parent

DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(_BASE / "documents")))
RESULTS_DIR   = Path(os.getenv("RESULTS_DIR",   str(_BASE / "results")))

DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_oid(doc_id: str) -> ObjectId:
    try:
        return ObjectId(doc_id)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid document id")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_documents():
    db = get_db()
    docs = await db.documents.find().sort("createdAt", -1).to_list(None)
    return [serialize_doc(d) for d in docs]


@router.post("/upload", status_code=201)
async def upload_document(file: UploadFile = File(...)):
    # Validate content type
    is_pdf = (
        (file.content_type or "").lower() == "application/pdf"
        or (file.filename or "").lower().endswith(".pdf")
    )
    if not is_pdf:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    if len(content) > 200 * 1024 * 1024:  # 200 MB
        raise HTTPException(status_code=413, detail="File too large (max 200 MB)")

    # Build stored filename:  {timestamp_ms}-{original_stem}.pdf
    original_stem = Path(file.filename or "upload").stem
    stored_filename = f"{int(time.time() * 1000)}-{original_stem}.pdf"
    pdf_path = DOCUMENTS_DIR / stored_filename
    pdf_path.write_bytes(content)

    # Derive where the structure JSON will live (agent writes here on index)
    structure_path = RESULTS_DIR / f"{Path(stored_filename).stem}_structure.json"

    now = datetime.now(timezone.utc)
    doc = {
        "name": original_stem,                 # human-readable name shown in UI
        "pdf_path": str(pdf_path.resolve()),   # absolute path used by the agent
        "structure_path": str(structure_path.resolve()),
        "indexed": False,
        "indexed_at": None,
        "description": "",
        "createdAt": now,
        "updatedAt": now,
    }

    db = get_db()
    result = await db.documents.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    db = get_db()
    doc = await db.documents.find_one({"_id": _to_oid(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return serialize_doc(doc)


@router.post("/", status_code=201)
async def create_document(body: dict):
    name     = (body.get("name") or "").strip()
    pdf_path = (body.get("pdf_path") or "").strip()
    if not name or not pdf_path:
        raise HTTPException(status_code=400, detail="name and pdf_path are required")

    structure_path = (body.get("structure_path") or "").strip()
    if not structure_path:
        stem = Path(pdf_path).stem
        structure_path = str(RESULTS_DIR / f"{stem}_structure.json")

    now = datetime.now(timezone.utc)
    doc = {
        "name": name,
        "pdf_path": pdf_path,
        "structure_path": structure_path,
        "indexed": False,
        "indexed_at": None,
        "description": (body.get("description") or "").strip(),
        "createdAt": now,
        "updatedAt": now,
    }

    db = get_db()
    result = await db.documents.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


@router.put("/{doc_id}")
async def update_document(doc_id: str, body: dict):
    body.pop("_id", None)  # never allow overwriting the id
    body["updatedAt"] = datetime.now(timezone.utc)

    db = get_db()
    result = await db.documents.find_one_and_update(
        {"_id": _to_oid(doc_id)},
        {"$set": body},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return serialize_doc(result)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    db = get_db()
    doc = await db.documents.find_one_and_delete({"_id": _to_oid(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted", "id": doc_id}


@router.post("/{doc_id}/mark-indexed")
async def mark_indexed(doc_id: str, body: dict):
    now = datetime.now(timezone.utc)
    update: dict = {
        "indexed": True,
        "indexed_at": now,
        "updatedAt": now,
    }
    sp = (body.get("structure_path") or "").strip()
    if sp:
        update["structure_path"] = sp

    db = get_db()
    result = await db.documents.find_one_and_update(
        {"_id": _to_oid(doc_id)},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return serialize_doc(result)
