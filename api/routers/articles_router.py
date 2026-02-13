from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas.ArticleSchema import ArticleCreate, ArticleResponse, ArticleUpdate
from dbase.collections.ArticleCollection import ArticleCollection

articles_router = APIRouter(prefix="/articles", tags=["articles"])


@articles_router.get("", response_model=List[ArticleResponse])
def list_articles(status: Optional[str] = Query(default=None, regex="^(draft|published)$")):
    collection = ArticleCollection()
    return collection.list(status=status)


@articles_router.get("/{slug}", response_model=ArticleResponse)
def get_article(slug: str):
    collection = ArticleCollection()
    article = collection.get(slug)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


@articles_router.post("", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
def create_article(payload: ArticleCreate):
    collection = ArticleCollection()
    try:
        return collection.create(payload.dict())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@articles_router.put("/{slug}", response_model=ArticleResponse)
def update_article(slug: str, payload: ArticleUpdate):
    collection = ArticleCollection()
    updates = payload.dict(exclude_unset=True)
    article = collection.update(slug, updates)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return article


@articles_router.delete("/{slug}")
def delete_article(slug: str):
    collection = ArticleCollection()
    deleted = collection.delete(slug)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return {"message": "Article deleted"}

