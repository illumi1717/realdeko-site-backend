import json
import hashlib
import os
import pickle
from typing import Any, Dict, List, Optional, get_args
from config import Post, localizer_types
from services.openai_api import OpenAIAPI
from config import classifier_types, localizer_types, Post

class AgentModule:
    def __init__(self):
        self.openai_api = OpenAIAPI()
        self.agent_id = None
        self.cache_file = os.path.join(os.path.dirname(__file__), "assistant_cache.pkl")
        self.localizer_values = get_args(localizer_types)
        languages_list = ", ".join(self.localizer_values)
        self.agent_prompt = f"""
            Ты агент для обработки обьявлений из Instagram их классификации, нормализации и локализации.
            Ты получаешь обьявление из Instagram и ты должен:

            - Классифицировать обьявление как одно из значений: {classifier_types}, если обьявление не соответствует классификации, то не должен его учитывать в ответе
            
            - Нормализовать обьявление, под моделью Post: {Post.model_json_schema()}

            - Локализовать обьявление, под языки: {languages_list}

            Ответ должен быть объектом без дополнительных полей, где каждый ключ — это локаль из списка [{languages_list}], и значение — пост под эту локаль. Нельзя пропускать локали и нельзя повторять одну локаль под разными ключами.
            В description должно быть короткое описание в несколько предложений.
            Если пост не описывает конкретный объект на аренду или продажу (рекламный, поздравительный, общий информационный), верни None и не выполняй нормализацию и локализацию.
        """

    def _build_response_schema(self) -> Dict[str, Any]:
        post_schema = Post.model_json_schema()
        if post_schema.get("type") == "object":
            post_schema.setdefault("additionalProperties", False)

        localized_posts_schema = {
            "type": "object",
            "properties": {locale: post_schema for locale in self.localizer_values},
            "required": list(self.localizer_values),
            "additionalProperties": False,
            "title": "LocalizedPostsPayload",
        }

        # OpenAI json_schema response_format requires the top-level schema to be
        # an object and disallows oneOf/anyOf at some levels. Keep the payload
        # under the "value" key and allow either the localized object or null.
        wrapped_schema = {
            "type": "object",
            "properties": {
                "value": {
                    "type": ["object", "null"],
                    "properties": localized_posts_schema["properties"],
                    "required": localized_posts_schema["required"],
                    "additionalProperties": False,
                }
            },
            "required": ["value"],
            "additionalProperties": False,
            "title": "LocalizedPostsResponse",
        }
        return wrapped_schema

    def _fingerprint(self, response_schema: Dict[str, Any]) -> str:
        schema_str = json.dumps(response_schema, sort_keys=True, ensure_ascii=False)
        payload = f"{self.agent_prompt.strip()}|{self.openai_api.model}|{schema_str}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_cached_agent(self) -> Optional[str]:
        if not os.path.exists(self.cache_file):
            return None
        try:
            with open(self.cache_file, "rb") as f:
                cache_data = pickle.load(f)
            return cache_data.get("assistant_id") if cache_data.get("fingerprint") == self.current_fingerprint else None
        except Exception:
            return None

    def _persist_cache(self, assistant_id: str):
        try:
            with open(self.cache_file, "wb") as f:
                pickle.dump({"assistant_id": assistant_id, "fingerprint": self.current_fingerprint}, f)
        except Exception:
            pass

    def create_agent(self):
        response_schema = self._build_response_schema()
        self.current_fingerprint = self._fingerprint(response_schema)
        cached_id = self._load_cached_agent()
        if cached_id:
            self.agent_id = cached_id
            print(f"Using cached agent id: {self.agent_id}")
            return

        self.agent_id = self.openai_api.create_agent(self.agent_prompt, response_schema=response_schema)
        self._persist_cache(self.agent_id)
        print(f"Agent created with id: {self.agent_id}")

    def process_data(self, messages: List[Dict[str, Any]]):
        prepared_messages: List[Dict[str, str]] = []
        source_caption = ""
        for msg in messages:
            content = msg.get("content", "")
            if not source_caption and msg.get("role") == "user":
                if isinstance(content, dict):
                    source_caption = content.get("caption", "") or ""
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            prepared_messages.append({**msg, "content": content})

        localized_posts_schema = self._build_response_schema()
        response = self.openai_api.send_messages(
            assistant_id=self.agent_id,
            messages=prepared_messages,
            response_schema=localized_posts_schema,
        )
        # OpenAI returns {"value": ...} for JSON schema responses. Normalize
        # the payload and return None when the model explicitly skips a post.
        if isinstance(response, dict) and "value" in response:
            return self._ensure_prices(response.get("value"))
        return self._ensure_prices(response)

    def _ensure_prices(self, localized_posts: Any) -> Optional[Dict[str, Any]]:
        """
        Minimal check: drop result if any locale has missing or non-positive price.
        """
        if not isinstance(localized_posts, dict):
            return None
        for _, post in localized_posts.items():
            if not isinstance(post, dict):
                return None
            price = post.get("price")
            print(price)
            if not isinstance(price, (int, float)) or price <= 0:
                return None
        return localized_posts