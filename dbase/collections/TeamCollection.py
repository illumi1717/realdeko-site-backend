import os
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from dbase.driver import DbaseDriver


class TeamCollection:
    """CRUD helper for team members stored in MongoDB."""

    def __init__(self, collection_name: Optional[str] = None):
        self.db = DbaseDriver()
        self.collection = self.db.get_collection(
            collection_name or os.getenv("MONGODB_TEAM_COLLECTION", "team_members")
        )

    @staticmethod
    def _serialize(document: Optional[dict]) -> Optional[dict]:
        if not document:
            return None
        doc = document.copy()
        doc["id"] = str(doc.pop("_id"))
        return doc

    def list(self) -> List[dict]:
        cursor = self.collection.find({}).sort("order", 1).sort("created_at", 1)
        return [self._serialize(doc) for doc in cursor]

    def get(self, member_id: str) -> Optional[dict]:
        document = self.collection.find_one({"_id": ObjectId(member_id)})
        return self._serialize(document)

    def create(self, data: dict) -> dict:
        now = datetime.utcnow()
        order = data.pop("order", None)
        if order is None:
            count = self.collection.count_documents({})
            order = count
        document = {
            **data,
            "order": order,
            "created_at": now,
            "updated_at": now,
        }
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return self._serialize(document)

    def update(self, member_id: str, updates: dict) -> Optional[dict]:
        if not updates:
            return self.get(member_id)
        updates["updated_at"] = datetime.utcnow()
        document = self.collection.find_one_and_update(
            {"_id": ObjectId(member_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._serialize(document)

    def delete(self, member_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(member_id)})
        return result.deleted_count == 1
