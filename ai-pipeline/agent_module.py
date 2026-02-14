import json
import hashlib
import os
import pickle
from typing import Any, Dict, List, Optional
from config import target_langs
from services.openai_api import OpenAIAPI


class AgentModule:
    def __init__(self):
        self.openai_api = OpenAIAPI()
        self.agent_id = None
        self.cache_file = os.path.join(os.path.dirname(__file__), "assistant_cache.pkl")

        langs_list = ", ".join(target_langs)

        self.agent_prompt = f"""
            Ты агент для обработки постов из Instagram агентства недвижимости.
            Ты получаешь пост из Instagram (caption и ссылку на изображение) и должен:

            1. Определить, является ли пост объявлением о сдаче/продаже недвижимости.
               Если пост НЕ является объявлением (рекламный, поздравительный, общий информационный), верни null.

            2. Классифицировать объявление как "rent" (аренда) или "sale" (продажа).

            3. Сгенерировать контент статьи на украинском языке (uk):
               - slug: URL-friendly идентификатор (латинские символы, нижний регистр, дефисы вместо пробелов, без спецсимволов)
               - title: короткий привлекательный заголовок
               - subtitle: краткое описание в одну строку
               - location: адрес или район
               - body: подробное описание (несколько абзацев, описывающих объект)
               - price: строка с ценой и валютой (например "25 000 CZK/měsíc"), пустая строка если цена неизвестна
               - price_on_request: true если цена не указана и должна быть "по запросу"
               - tags: релевантные теги (например ["квартира", "центр", "2+kk"])
               - key_metrics: ключевые характеристики объекта (площадь, количество комнат, этаж и т.д.)
                 Каждая метрика имеет: label (название), value (значение), helper (пояснение, пустая строка если не нужно)

            4. Перевести title, subtitle, location, body, tags и key_metrics на языки: {langs_list}

            Ответ должен быть JSON-объектом с полями базовой статьи и полем translations с переводами на каждый язык.
            Если пост не является объявлением — верни null.
        """

    def _build_response_schema(self) -> Dict[str, Any]:
        """Build JSON schema compatible with OpenAI strict mode for article drafts."""

        key_metric_schema = {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "value": {"type": "string"},
                "helper": {"type": "string"},
            },
            "required": ["label", "value", "helper"],
            "additionalProperties": False,
        }

        translation_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "location": {"type": "string"},
                "body": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "key_metrics": {"type": "array", "items": key_metric_schema},
            },
            "required": ["title", "subtitle", "location", "body", "tags", "key_metrics"],
            "additionalProperties": False,
        }

        draft_schema = {
            "type": "object",
            "properties": {
                "post_type": {"type": "string", "enum": ["rent", "sale"]},
                "slug": {"type": "string"},
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "location": {"type": "string"},
                "body": {"type": "string"},
                "price": {"type": "string"},
                "price_on_request": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "key_metrics": {"type": "array", "items": key_metric_schema},
                "translations": {
                    "type": "object",
                    "properties": {
                        lang: translation_schema for lang in target_langs
                    },
                    "required": list(target_langs),
                    "additionalProperties": False,
                },
            },
            "required": [
                "post_type", "slug", "title", "subtitle", "location",
                "body", "price", "price_on_request", "tags", "key_metrics",
                "translations",
            ],
            "additionalProperties": False,
        }

        # Wrap with nullable support (null = post is not a listing)
        wrapped_schema = {
            "type": "object",
            "properties": {
                "value": {
                    "type": ["object", "null"],
                    "properties": draft_schema["properties"],
                    "required": draft_schema["required"],
                    "additionalProperties": False,
                }
            },
            "required": ["value"],
            "additionalProperties": False,
            "title": "ArticleDraftResponse",
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

    def process_post(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single Instagram post and return article draft data,
        or None if the post is not a listing.
        """
        content = json.dumps(post, ensure_ascii=False)
        messages = [{"role": "user", "content": content}]

        response_schema = self._build_response_schema()
        response = self.openai_api.send_messages(
            assistant_id=self.agent_id,
            messages=messages,
            response_schema=response_schema,
        )

        # OpenAI returns {"value": ...} — extract the inner value
        if isinstance(response, dict) and "value" in response:
            return response.get("value")
        return response
