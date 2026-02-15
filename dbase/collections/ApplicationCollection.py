import os
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pymongo import ReturnDocument

from dbase.driver import DbaseDriver


class ApplicationCollection:
    """
    CRUD helper for applications (website form submissions) stored in MongoDB.
    """

    def __init__(self, collection_name: Optional[str] = None):
        self.db = DbaseDriver()
        self.collection = self.db.get_collection(
            collection_name or os.getenv("MONGODB_APPLICATIONS_COLLECTION", "applications")
        )

    @staticmethod
    def _serialize(document: Optional[dict]) -> Optional[dict]:
        if not document:
            return None
        doc = document.copy()
        doc["id"] = str(doc.pop("_id"))
        return doc

    def list(self, status: Optional[str] = None) -> List[dict]:
        query = {}
        if status:
            query["status"] = status
        cursor = self.collection.find(query).sort("created_at", -1)
        return [self._serialize(doc) for doc in cursor]

    def get(self, application_id: str) -> Optional[dict]:
        document = self.collection.find_one({"_id": ObjectId(application_id)})
        return self._serialize(document)

    def create(self, data: dict) -> dict:
        now = datetime.utcnow()
        document = {
            **data,
            "status": "new",
            "notes": "",
            "created_at": now,
            "updated_at": now,
        }
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return self._serialize(document)

    def update_status(self, application_id: str, status: str) -> Optional[dict]:
        document = self.collection.find_one_and_update(
            {"_id": ObjectId(application_id)},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        return self._serialize(document)

    def update_notes(self, application_id: str, notes: str) -> Optional[dict]:
        document = self.collection.find_one_and_update(
            {"_id": ObjectId(application_id)},
            {"$set": {"notes": notes, "updated_at": datetime.utcnow()}},
            return_document=ReturnDocument.AFTER,
        )
        return self._serialize(document)

    def delete(self, application_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(application_id)})
        return result.deleted_count == 1

