import os
from datetime import datetime
from typing import List, Optional

from pymongo import ReturnDocument

from dbase.driver import DbaseDriver


class ArticleCollection:
    """
    CRUD helper for articles stored in MongoDB.
    Documents are keyed by slug (stored in the `_id` field).
    """

    def __init__(self, collection_name: Optional[str] = None):
        self.db = DbaseDriver()
        self.collection = self.db.get_collection(collection_name or os.getenv("MONGODB_ARTICLES_COLLECTION", "articles"))

    def _serialize(self, document: Optional[dict]) -> Optional[dict]:
        if not document:
            return None

        doc = document.copy()
        doc["id"] = str(doc.get("_id"))
        doc["slug"] = doc.get("_id")
        doc.pop("_id", None)

        for key in ("created_at", "updated_at"):
            if isinstance(doc.get(key), datetime):
                doc[key] = doc[key]

        return doc

    def list(self, status: Optional[str] = None) -> List[dict]:
        query = {"status": status} if status else {}
        return [self._serialize(doc) for doc in self.collection.find(query)]

    def get(self, slug: str) -> Optional[dict]:
        document = self.collection.find_one({"_id": slug})
        return self._serialize(document)

    def create(self, data: dict) -> dict:
        slug = data.get("slug")
        if not slug:
            raise ValueError("Slug is required")

        if self.collection.find_one({"_id": slug}):
            raise ValueError("Article with this slug already exists")

        now = datetime.utcnow()
        document = {
            "_id": slug,
            **data,
            "created_at": now,
            "updated_at": now,
        }

        self.collection.insert_one(document)
        return self._serialize(document)

    def update(self, slug: str, updates: dict) -> Optional[dict]:
        if not updates:
            existing = self.collection.find_one({"_id": slug})
            return self._serialize(existing)

        updates["updated_at"] = datetime.utcnow()

        document = self.collection.find_one_and_update(
            {"_id": slug}, {"$set": updates}, return_document=ReturnDocument.AFTER
        )

        return self._serialize(document)

    def delete(self, slug: str) -> bool:
        result = self.collection.delete_one({"_id": slug})
        return result.deleted_count == 1

