"""
Shared serialization helpers.
"""

from datetime import datetime
from bson import ObjectId


def serialize_doc(doc: dict) -> dict:
    """
    Convert a raw Motor/PyMongo document dict to a JSON-serializable dict:
      - _id ObjectId  →  string
      - datetime fields  →  ISO-8601 string
      - datetime inside messages[].timestamp  →  ISO-8601 string
    """
    doc = dict(doc)

    # ObjectId → string
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])

    # Top-level datetime fields
    for field in ("createdAt", "updatedAt", "indexed_at"):
        if field in doc and isinstance(doc[field], datetime):
            doc[field] = doc[field].isoformat()

    # Nested message timestamps
    if "messages" in doc and doc["messages"]:
        serialized_messages = []
        for msg in doc["messages"]:
            msg = dict(msg)
            if "timestamp" in msg and isinstance(msg["timestamp"], datetime):
                msg["timestamp"] = msg["timestamp"].isoformat()
            serialized_messages.append(msg)
        doc["messages"] = serialized_messages

    return doc


def parse_message_timestamps(messages: list[dict]) -> list[dict]:
    """
    Parse ISO-8601 timestamp strings inside a messages list into datetime objects
    so they are stored correctly in MongoDB.
    """
    result = []
    for msg in messages:
        msg = dict(msg)
        ts = msg.get("timestamp")
        if isinstance(ts, str):
            try:
                msg["timestamp"] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                pass
        result.append(msg)
    return result
