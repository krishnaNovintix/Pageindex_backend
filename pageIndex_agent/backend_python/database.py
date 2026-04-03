"""
Async MongoDB client singleton using Motor.
Call connect_db() on startup and close_db() on shutdown (handled in main.py lifespan).
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database is not connected. Call connect_db() first.")
    return _db


async def connect_db() -> None:
    global _client, _db
    mongo_uri = os.getenv("MONGO_URI") #, "mongodb://localhost:27017/pageindex"

    _client = AsyncIOMotorClient(mongo_uri)

    # Parse database name from URI; fall back to "pageindex"
    # Split on "/" to get the path segment after the host, strip query params.
    # Guard against extracting the hostname (contains ".") when no db path is present.
    _path_segment = mongo_uri.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    db_name = _path_segment if _path_segment and "." not in _path_segment else "pageindex"
    _db = _client[db_name]

    # Confirm the connection is alive
    await _client.admin.command("ping")
    print(f"Connected to MongoDB: {mongo_uri}  (db={db_name})")


async def close_db() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
