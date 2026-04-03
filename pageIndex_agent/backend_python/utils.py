"""
Shared serialization helpers.
"""

import os
from pathlib import Path
from datetime import datetime
from bson import ObjectId


# ---------------------------------------------------------------------------
# Path resolution helper
# ---------------------------------------------------------------------------

def resolve_stored_path(stored: str, fallback_dir: str | None = None) -> str:
    """
    Return an OS-correct absolute path for a path that was stored in MongoDB.

    Handles the common case where a path was stored on Windows
    (e.g. D:\\personal\\...\\documents\\file.pdf) but the server is now
    running on Linux (Render).  Strategy:

    1. Try the path as-is (works when both OS match).
    2. Strip everything up to the last directory separator and look for
       the bare filename inside ``fallback_dir`` (e.g. DOCUMENTS_DIR).
    3. Return the best candidate; callers raise 404 if the file still
       doesn't exist.
    """
    candidate = os.path.abspath(stored)
    if os.path.isfile(candidate):
        return candidate

    if fallback_dir:
        filename = Path(stored).name          # works for both / and \
        fallback = Path(fallback_dir) / filename
        if fallback.is_file():
            return str(fallback)

    return candidate   # let caller decide what to do



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
