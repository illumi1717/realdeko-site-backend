import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, status
from openai import OpenAI

# Load .env from the ai-pipeline directory where OPENAI_API_KEY is stored
_env_path = Path(__file__).resolve().parents[2] / "ai-pipeline" / ".env"
load_dotenv(_env_path)

from api.schemas.ArticleSchema import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
    LanguageCode,
    LocalizeRequest,
    LocalizeResponse,
)
from dbase.collections.ArticleCollection import ArticleCollection

articles_router = APIRouter(prefix="/articles", tags=["articles"])

LANGUAGE_NAMES = {"cs": "Czech", "en": "English", "uk": "Ukrainian", "ru": "Russian"}


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


@articles_router.post("/{slug}/localize", response_model=LocalizeResponse)
def localize_article(slug: str, payload: LocalizeRequest):
    """Translate base Ukrainian article content into English, Czech, and Russian."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

    # Base content is always Ukrainian; targets are always en, cs, ru
    source_lang = "uk"
    target_langs = ["en", "cs", "ru"]

    collection = ArticleCollection()
    article = collection.get(slug)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    # Build the source content dict (Ukrainian base) to send to the model
    source_content = {
        "title": article.get("title", ""),
        "subtitle": article.get("subtitle", ""),
        "location": article.get("location", ""),
        "body": article.get("body", ""),
    }

    key_metrics = article.get("key_metrics") or []
    if key_metrics:
        source_content["key_metrics"] = [
            {"label": m.get("label", ""), "value": m.get("value", ""), "helper": m.get("helper", "")}
            for m in key_metrics
        ]

    target_lang_names = {code: LANGUAGE_NAMES[code] for code in target_langs}

    target_langs_description = ", ".join(
        f'"{code}" ({name})' for code, name in target_lang_names.items()
    )

    system_prompt = (
        "You are a professional real-estate copywriter and translator. "
        "You receive a property listing in Ukrainian and translate it into the requested target languages. "
        "Preserve the tone, marketing appeal, and all factual details (numbers, addresses, proper nouns). "
        "Location names that are proper nouns (street names, city districts) should stay in their original form. "
        "Return ONLY valid JSON — no markdown fences, no commentary."
    )

    user_prompt = (
        f"Source language: Ukrainian (uk).\n"
        f"Target languages: {target_langs_description}.\n\n"
        f"Source content (Ukrainian):\n{json.dumps(source_content, ensure_ascii=False, indent=2)}\n\n"
        "Translate all text fields into each target language. "
        "Return a JSON object with this exact structure:\n"
        "{\n"
        '  "translations": {\n'
        '    "<lang_code>": {\n'
        '      "title": "...",\n'
        '      "subtitle": "...",\n'
        '      "location": "...",\n'
        '      "body": "...",\n'
        '      "key_metrics": [{"label": "...", "value": "...", "helper": "..."}]\n'
        "    }\n"
        "  }\n"
        "}\n"
        "Include a key for every target language code (en, cs, ru). "
        "If there are no key_metrics in the source, omit the key_metrics field."
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = response.choices[0].message.content or ""
        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        result = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned invalid JSON. Please try again.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI localization failed: {exc}",
        )

    return result

