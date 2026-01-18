import os
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


class DbaseDriver:
    """
    Thin wrapper around MongoClient that:
    - Reads connection settings from env (MONGODB_URI, MONGODB_DB)
    - Exposes a helper to obtain a collection handle.
    """

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        self.uri = uri or os.getenv("MONGODB_URI")
        if not self.uri:
            raise ValueError("MONGODB_URI is not set. Add it to .env or pass uri explicitly.")

        self.db_name = db_name or os.getenv("MONGODB_DB", "realdeko")
        self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[self.db_name]

    def get_collection(self, collection_name: str):
        return self.db[collection_name]