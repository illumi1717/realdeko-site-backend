import os
import re
import uuid
import unicodedata
from pathlib import Path

import requests

from agent_module import AgentModule
from services.instagram_api import InstagramAPI
from dbase.collections.ArticleCollection import ArticleCollection


USERNAME = "realdeko_group_official"

# Use the same MEDIA_ROOT as the API server.
# Default: ../media relative to ai-pipeline/ → backend/media/
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", os.path.join(os.path.dirname(__file__), "..", "media")))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def normalize_posts(raw_posts):
    """Extract relevant fields from raw Instagram API response."""
    edges = raw_posts.get("result", {}).get("edges", [])
    normalized = []

    for post in edges:
        try:
            node = post["node"]
            code = node["code"]
            normalized.append(
                {
                    "instagram_id": node["id"],
                    "code": code,
                    "caption": node.get("caption", {}).get("text", ""),
                    "image_url": node["image_versions2"]["candidates"][0]["url"],
                    "post_url": f"https://www.instagram.com/p/{code}",
                }
            )
        except Exception as e:
            print(f"Error processing post {post.get('node', {}).get('id', '<unknown>')}: {e}")

    return normalized


def slugify(text: str, max_length: int = 60) -> str:
    """Simple slugify: transliterate, lowercase, replace non-alnum with hyphens."""
    # Basic Cyrillic → Latin transliteration map
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'і': 'i', 'ї': 'yi', 'є': 'ye', 'ґ': 'g',
        'ě': 'e', 'š': 's', 'č': 'c', 'ř': 'r', 'ž': 'z', 'ý': 'y',
        'á': 'a', 'í': 'i', 'é': 'e', 'ú': 'u', 'ů': 'u', 'ň': 'n',
        'ť': 't', 'ď': 'd', 'ö': 'o', 'ü': 'u', 'ä': 'a',
    }
    text = text.lower()
    result = []
    for ch in text:
        if ch in translit_map:
            result.append(translit_map[ch])
        else:
            result.append(ch)
    text = "".join(result)

    # Normalize unicode and keep only ASCII alnum + hyphens
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)

    if len(text) > max_length:
        text = text[:max_length].rstrip("-")

    return text


def download_image(url: str) -> str:
    """
    Download an image from a URL and save it locally to MEDIA_ROOT.
    Returns the relative media path (e.g. /media/<filename>.jpg).
    """
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()

        # Determine file extension from Content-Type header
        content_type = resp.headers.get("Content-Type", "")
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        ext = ext_map.get(content_type.split(";")[0].strip(), ".jpg")

        filename = f"{uuid.uuid4().hex}{ext}"
        target_path = MEDIA_ROOT / filename

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"  → Downloaded image: {filename} ({target_path.stat().st_size // 1024} KB)")
        return f"/media/{filename}"

    except Exception as e:
        print(f"  → Failed to download image: {e}")
        return ""


def build_article_document(ai_result: dict, instagram_post: dict) -> dict:
    """
    Convert AI agent output + Instagram post data into a document
    ready for ArticleCollection.create().
    """
    # Ensure slug is unique by appending Instagram code
    base_slug = ai_result.get("slug", "")
    if not base_slug:
        base_slug = slugify(ai_result.get("title", "post"))
    instagram_code = instagram_post.get("code", "")
    slug = f"{base_slug}-{instagram_code}" if instagram_code else base_slug

    # Build translations dict matching ArticleSchema format
    translations = {}
    ai_translations = ai_result.get("translations", {})
    for lang_code, t in ai_translations.items():
        translations[lang_code] = {
            "title": t.get("title"),
            "subtitle": t.get("subtitle"),
            "location": t.get("location"),
            "body": t.get("body"),
            "tags": t.get("tags"),
            "key_metrics": t.get("key_metrics"),
        }

    # Determine price fields
    price = ai_result.get("price", "")
    price_on_request = ai_result.get("price_on_request", False)
    if not price:
        price_on_request = True

    return {
        "slug": slug,
        "title": ai_result.get("title", ""),
        "subtitle": ai_result.get("subtitle", ""),
        "location": ai_result.get("location", ""),
        "cover_url": instagram_post.get("local_image_url") or instagram_post.get("image_url", ""),
        "body": ai_result.get("body", ""),
        "price": price if price else None,
        "price_on_request": price_on_request,
        "highlight": False,
        "status": "draft",
        "post_type": ai_result.get("post_type", "sale"),
        "tags": ai_result.get("tags", []),
        "key_metrics": ai_result.get("key_metrics", []),
        "gallery": [],
        "blocks": [],
        "translations": translations,
        # Track source for deduplication
        "source": "instagram",
        "source_instagram_id": instagram_post.get("instagram_id"),
        "source_post_url": instagram_post.get("post_url", ""),
    }


def sync_instagram_posts():
    """
    Main pipeline: fetch Instagram posts, process with AI,
    and save new ones as draft articles.
    """
    # 1. Fetch posts from Instagram
    instagram_api = InstagramAPI()
    raw_posts = instagram_api.get_posts(USERNAME)
    normalized_posts = normalize_posts(raw_posts)

    if not normalized_posts:
        print("No posts received from Instagram.")
        return

    print(f"Fetched {len(normalized_posts)} posts from Instagram.")

    # 2. Check which posts are already imported
    collection = ArticleCollection()
    existing_instagram_ids = set(collection.get_source_instagram_ids())

    new_posts = [p for p in normalized_posts if p["instagram_id"] not in existing_instagram_ids]
    if not new_posts:
        print("No new posts to process. All posts already imported.")
        return

    print(f"Found {len(new_posts)} new posts to process.")

    # 3. Create AI agent
    agent = AgentModule()
    agent.create_agent()

    # 4. Process each new post
    imported = 0
    skipped = 0

    for post in new_posts:
        print(f"\nProcessing Instagram post {post['instagram_id']} ({post['post_url']})...")

        ai_result = agent.process_post(post)

        if ai_result is None:
            print(f"  → Skipped (not a listing).")
            skipped += 1
            continue

        # Download cover image locally before saving the article
        image_url = post.get("image_url", "")
        if image_url:
            local_path = download_image(image_url)
            if local_path:
                post["local_image_url"] = local_path

        # Build article document and save as draft
        article_doc = build_article_document(ai_result, post)

        try:
            created = collection.create(article_doc)
            print(f"  → Created draft article: {created['slug']}")
            imported += 1
        except ValueError as e:
            # Slug already exists — skip
            print(f"  → Skipped (slug conflict): {e}")
            skipped += 1
        except Exception as e:
            print(f"  → Error saving article: {e}")
            skipped += 1

    print(f"\nDone! Imported: {imported}, Skipped: {skipped}")


if __name__ == "__main__":
    sync_instagram_posts()
