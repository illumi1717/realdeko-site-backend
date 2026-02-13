from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas.ArticleSchema import ArticleCreate, ArticleResponse, ArticleUpdate, LanguageCode
from dbase.collections.ArticleCollection import ArticleCollection

articles_router = APIRouter(prefix="/articles", tags=["articles"])


def apply_translation(article: dict, lang: Optional[LanguageCode]) -> dict:
    if not lang:
        return article

    translations = article.get("translations") or {}
    localized = translations.get(lang)
    if not localized:
        return article

    merged = article.copy()
    for field in ("title", "subtitle", "location", "body", "tags", "key_metrics", "gallery", "blocks"):
        value = localized.get(field) if isinstance(localized, dict) else getattr(localized, field, None)
        if value is not None:
            merged[field] = value
    return merged


@articles_router.get("", response_model=List[ArticleResponse])
def list_articles(
    status: Optional[str] = Query(default=None, regex="^(draft|published)$"),
    lang: Optional[LanguageCode] = Query(default=None, description="Optional language code to localize response"),
):
    collection = ArticleCollection()
    articles = collection.list(status=status)
    return [apply_translation(article, lang) for article in articles]


@articles_router.get("/{slug}", response_model=ArticleResponse)
def get_article(
    slug: str,
    lang: Optional[LanguageCode] = Query(default=None, description="Optional language code to localize response"),
):
    collection = ArticleCollection()
    article = collection.get(slug)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return apply_translation(article, lang)


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

