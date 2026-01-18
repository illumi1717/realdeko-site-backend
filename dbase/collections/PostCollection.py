import os
from typing import List, Optional

from dbase.driver import DbaseDriver


class PostCollection:
    """
    Provides CRUD helpers for Instagram posts stored in MongoDB.
    Each document is keyed by the Instagram post id (_id).
    """

    def __init__(self, collection_name: Optional[str] = None):
        self.db = DbaseDriver()
        self.collection = self.db.get_collection(collection_name or os.getenv("MONGODB_COLLECTION", "posts"))

    def get_all_posts(self) -> List[dict]:
        return list(self.collection.find({}))

    def upsert_post(self, instagram_id: str, document: dict):
        document["_id"] = instagram_id
        return self.collection.update_one({"_id": instagram_id}, {"$set": document}, upsert=True)

    def get_instagram_ids(self) -> List[str]:
        return [doc["_id"] for doc in self.collection.find({}, {"_id": 1})]

    def get_post_by_id(self, instagram_id: str):
        return self.collection.find_one({"_id": instagram_id})

    def delete_by_ids(self, ids: List[str]):
        if not ids:
            return None
        return self.collection.delete_many({"_id": {"$in": ids}})