"""
/api/conversations routes

GET    /          — list all conversations (messages excluded for performance)
GET    /{conv_id} — get one conversation with full messages
POST   /          — create a new conversation
PUT    /{conv_id} — update title and/or messages
DELETE /{conv_id} — delete a conversation
"""

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pymongo import ReturnDocument

from database import get_db
from utils import serialize_doc, parse_message_timestamps

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_oid(conv_id: str) -> ObjectId:
    try:
        return ObjectId(conv_id)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid conversation id")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_conversations():
    """Return all conversations sorted newest first, without message bodies."""
    db = get_db()
    # Exclude the messages array for the list view (matches Mongoose behaviour)
    convs = await db.conversations.find({}, {"messages": 0}).sort("updatedAt", -1).to_list(None)
    return [serialize_doc(c) for c in convs]


@router.get("/{conv_id}")
async def get_conversation(conv_id: str):
    """Return a single conversation with its full message history."""
    db = get_db()
    conv = await db.conversations.find_one({"_id": _to_oid(conv_id)})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return serialize_doc(conv)


@router.post("/", status_code=201)
async def create_conversation(body: dict):
    now = datetime.now(timezone.utc)

    messages = parse_message_timestamps(body.get("messages") or [])

    conv = {
        "title":         (body.get("title") or "New Chat").strip(),
        "document_id":   body.get("document_id") or None,
        "document_name": body.get("document_name") or None,
        "messages":      messages,
        "createdAt":     now,
        "updatedAt":     now,
    }

    db = get_db()
    result = await db.conversations.insert_one(conv)
    conv["_id"] = result.inserted_id
    return serialize_doc(conv)


@router.put("/{conv_id}")
async def update_conversation(conv_id: str, body: dict):
    body.pop("_id", None)  # never allow overwriting the id

    # Re-parse message timestamps if the caller is updating the messages array
    if "messages" in body:
        body["messages"] = parse_message_timestamps(body["messages"] or [])

    body["updatedAt"] = datetime.now(timezone.utc)

    db = get_db()
    result = await db.conversations.find_one_and_update(
        {"_id": _to_oid(conv_id)},
        {"$set": body},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return serialize_doc(result)


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str):
    db = get_db()
    conv = await db.conversations.find_one_and_delete({"_id": _to_oid(conv_id)})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted", "id": conv_id}
