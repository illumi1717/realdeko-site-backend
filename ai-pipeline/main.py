from agent_module import AgentModule
from services.instagram_api import InstagramAPI
from dbase.collections.PostCollection import PostCollection


USERNAME = "realdeko_group_official"


def normalize_posts(raw_posts):
    edges = raw_posts.get("result", {}).get("edges", [])
    normalized_posts = []

    for post in edges:
        try:
            node = post["node"]
            normalized_posts.append(
                {
                    "id": node["id"],
                    "caption": node.get("caption", {}).get("text", ""),
                    "image_url": node["image_versions2"]["candidates"][0]["url"],
                    "post_url": "https://www.instagram.com/p/" + node["code"],
                }
            )
        except Exception as e:
            print(f"Error processing post {post.get('node', {}).get('id', '<unknown>')}: {e}")
    return normalized_posts


def sync_instagram_posts():
    instagram_api = InstagramAPI()
    posts = instagram_api.get_posts(USERNAME)

    normalized_posts = normalize_posts(posts)
    if not normalized_posts:
        print("No posts received from Instagram.")
        return

    collection = PostCollection()
    existing_ids = set(collection.get_instagram_ids())
    current_ids = {post["id"] for post in normalized_posts}

    # Remove posts that disappeared from Instagram.
    removed_ids = list(existing_ids - current_ids)
    if removed_ids:
        collection.delete_by_ids(removed_ids)
        print(f"Removed {len(removed_ids)} posts that no longer exist on Instagram.")

    # Process only new posts.
    new_posts = [post for post in normalized_posts if post["id"] not in existing_ids]
    if not new_posts:
        print("No new posts to process.")
        return

    agent = AgentModule()
    agent.create_agent()

    for post in new_posts:
        response = agent.process_data(messages=[{"role": "user", "content": post}])
        if response is None:
            print(f"Skipped post {post['id']} — not a rent/sale listing.")
            continue
        collection.upsert_post(
            instagram_id=post["id"],
            document={
                "instagram_id": post["id"],
                "post_url": post["post_url"],
                "photo_url": post["image_url"],
                "caption": post["caption"],
                "localized_posts": response,
                "source": "instagram",
            },
        )
        print(f"Processed and saved post {post['id']}")


if __name__ == "__main__":
    sync_instagram_posts()