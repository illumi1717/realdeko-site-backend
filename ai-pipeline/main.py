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
    """Extract relevant fields from raw Instagram API response.

    Handles three Instagram media types:
      media_type 1 → photo
      media_type 2 → video / reel
      media_type 8 → carousel (album of photos / videos)
    """
    edges = raw_posts.get("result", {}).get("edges", [])
    normalized = []

    for post in edges:
        try:
            node = post["node"]
            code = node["code"]
            media_type = node.get("media_type", 1)  # 1=photo, 2=video, 8=carousel

            # --- cover image (always present as a thumbnail) ---
            image_url = ""
            image_versions = node.get("image_versions2", {}).get("candidates", [])
            if image_versions:
                image_url = image_versions[0]["url"]

            # --- video URL (only for video posts, media_type 2) ---
            video_url = ""
            video_versions = node.get("video_versions", [])
            if video_versions:
                video_url = video_versions[0]["url"]

            # --- carousel media (media_type 8) ---
            carousel_items = []
            if media_type == 8:
                for item in node.get("carousel_media", []):
                    item_type = item.get("media_type", 1)
                    item_data = {"media_type": item_type}

                    item_images = item.get("image_versions2", {}).get("candidates", [])
                    if item_images:
                        item_data["image_url"] = item_images[0]["url"]

                    item_videos = item.get("video_versions", [])
                    if item_videos:
                        item_data["video_url"] = item_videos[0]["url"]

                    carousel_items.append(item_data)

            normalized.append(
                {
                    "instagram_id": node["id"],
                    "code": code,
                    "media_type": media_type,
                    "caption": node.get("caption", {}).get("text", ""),
                    "image_url": image_url,
                    "video_url": video_url,
                    "carousel_media": carousel_items,
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


def download_media(url: str) -> str:
    """
    Download media (image or video) from a URL and save it locally to MEDIA_ROOT.
    Returns the relative media path (e.g. /media/<filename>.jpg or /media/<filename>.mp4).
    """
    try:
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()

        # Determine file extension from Content-Type header
        content_type = resp.headers.get("Content-Type", "")
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/webm": ".webm",
        }
        ct_clean = content_type.split(";")[0].strip()
        ext = ext_map.get(ct_clean, "")
        if not ext:
            # Fallback: guess from content-type family
            ext = ".mp4" if ct_clean.startswith("video/") else ".jpg"

        filename = f"{uuid.uuid4().hex}{ext}"
        target_path = MEDIA_ROOT / filename

        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        kind = "video" if ext in (".mp4", ".mov", ".webm") else "image"
        size_kb = target_path.stat().st_size // 1024
        print(f"  → Downloaded {kind}: {filename} ({size_kb} KB)")
        return f"/media/{filename}"

    except Exception as e:
        print(f"  → Failed to download media: {e}")
        return ""


def build_article_document(ai_result: dict, instagram_post: dict) -> dict:
    """
    Convert AI agent output + Instagram post data into a document
    ready for ArticleCollection.create().

    Supports photo, video and carousel Instagram posts:
    - Video posts populate cover_url (thumbnail) and video_url.
    - Carousel posts populate gallery with all downloaded media items.
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

    # Determine price fields — guard against AI putting non-monetary text into price
    price = ai_result.get("price", "")
    INVALID_PRICES = {
        # deal types
        "rent", "sale", "аренда", "продажа", "оренда", "продаж",
        # property types (uk/ru/cs/en)
        "квартира", "будинок", "дом", "кімната", "комната", "студія", "студия",
        "byt", "dům", "apartmán", "pokoj",
        "apartment", "house", "flat", "studio", "room",
    }
    price_lower = price.strip().lower()
    if price_lower in INVALID_PRICES or (price_lower and not any(ch.isdigit() for ch in price_lower)):
        print(f"  ⚠ AI put '{price}' into price field instead of a monetary value — resetting to empty.")
        price = ""
    price_on_request = ai_result.get("price_on_request", False)
    if not price:
        price_on_request = True

    # --- Cover image / video ---
    cover_url = instagram_post.get("local_image_url") or instagram_post.get("image_url", "")
    video_url = instagram_post.get("local_video_url") or instagram_post.get("video_url", "") or None

    # --- Gallery from carousel items ---
    gallery = []
    for item in instagram_post.get("local_carousel_media", []):
        src = item.get("local_image_url") or item.get("image_url", "")
        if src:
            gallery.append({"src": src})

    return {
        "slug": slug,
        "title": ai_result.get("title", ""),
        "subtitle": ai_result.get("subtitle", ""),
        "location": ai_result.get("location", ""),
        "cover_url": cover_url,
        "video_url": video_url,
        "body": ai_result.get("body", ""),
        "price": price if price else None,
        "price_on_request": price_on_request,
        "highlight": False,
        "status": "draft",
        "post_type": ai_result.get("post_type", "sale"),
        "tags": ai_result.get("tags", []),
        "key_metrics": ai_result.get("key_metrics", []),
        "gallery": gallery,
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
        media_type = post.get("media_type", 1)
        media_label = {1: "photo", 2: "video", 8: "carousel"}.get(media_type, "unknown")
        print(f"\nProcessing Instagram {media_label} post {post['instagram_id']} ({post['post_url']})...")

        ai_result = agent.process_post(post)

        if ai_result is None:
            print(f"  → Skipped (not a listing).")
            skipped += 1
            continue

        # --- Download cover image ---
        image_url = post.get("image_url", "")
        if image_url:
            local_path = download_media(image_url)
            if local_path:
                post["local_image_url"] = local_path

        # --- Download video (for video posts, media_type 2) ---
        video_url = post.get("video_url", "")
        if video_url:
            local_video = download_media(video_url)
            if local_video:
                post["local_video_url"] = local_video

        # --- Download carousel items (for carousel posts, media_type 8) ---
        if media_type == 8 and post.get("carousel_media"):
            local_carousel = []
            for idx, item in enumerate(post["carousel_media"]):
                print(f"  → Downloading carousel item {idx + 1}/{len(post['carousel_media'])}...")
                local_item = {}

                # Download image (thumbnail for videos, full image for photos)
                item_image = item.get("image_url", "")
                if item_image:
                    local_img = download_media(item_image)
                    if local_img:
                        local_item["local_image_url"] = local_img

                # Download video if carousel item is a video
                item_video = item.get("video_url", "")
                if item_video:
                    local_vid = download_media(item_video)
                    if local_vid:
                        local_item["local_video_url"] = local_vid

                local_item["media_type"] = item.get("media_type", 1)
                local_carousel.append(local_item)

            post["local_carousel_media"] = local_carousel

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
