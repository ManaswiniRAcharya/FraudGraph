from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27018"
DB_NAME = "fraudgraph"

_client = None


def get_db():
    """Return the fraudgraph database, creating one shared connection on first use."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client[DB_NAME]
