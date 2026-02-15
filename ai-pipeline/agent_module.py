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
            Ти — агент для обробки постів з Instagram агентства нерухомості.
            Ти отримуєш пост з Instagram (caption та посилання на зображення) і маєш:

            1. Визначити, чи є пост оголошенням про оренду/продаж нерухомості.
               Якщо пост НЕ є оголошенням (рекламний, привітальний, загальноінформаційний) — поверни null.

            2. Класифікувати оголошення як "rent" (оренда) або "sale" (продаж).
               Результат записати ТІЛЬКИ в поле post_type. Не плутай тип оголошення з ціною!

            3. Згенерувати контент статті ОБОВ'ЯЗКОВО УКРАЇНСЬКОЮ МОВОЮ (uk).
               Усі текстові поля базової статті (title, subtitle, location, body, tags, key_metrics)
               МАЮТЬ бути написані виключно українською мовою. Це обов'язкова вимога.
               - slug: URL-friendly ідентифікатор (латинські символи, нижній регістр, дефіси замість пробілів, без спецсимволів)
               - title: короткий привабливий заголовок (УКРАЇНСЬКОЮ)
               - subtitle: короткий опис в один рядок (УКРАЇНСЬКОЮ)
               - location: адреса або район (УКРАЇНСЬКОЮ, але власні назви вулиць/районів залишати в оригінальній формі)
               - body: детальний опис (кілька абзаців, що описують об'єкт) (УКРАЇНСЬКОЮ)
               - price: ЧИСЛОВА ціна з валютою, вилучена з тексту поста (наприклад "25 000 CZK/měsíc", "150 000 €", "5 500 000 CZK").
                 Це має бути ТІЛЬКИ грошова сума з валютою. НЕ пиши сюди тип оголошення (rent/sale/оренда/продаж).
                 Якщо в тексті поста немає конкретної ціни — постав порожній рядок "".
               - price_on_request: true ТІЛЬКИ якщо ціна не знайдена в тексті поста (тобто price — порожній рядок).
                 Якщо ціна вказана — став false.
               - tags: релевантні теги УКРАЇНСЬКОЮ (наприклад ["квартира", "центр", "2+kk"])
               - key_metrics: ключові характеристики об'єкта (площа, кількість кімнат, поверх тощо)
                 Кожна метрика має: label (назва УКРАЇНСЬКОЮ), value (значення), helper (пояснення УКРАЇНСЬКОЮ, порожній рядок якщо не потрібно)

            ВАЖЛИВО щодо поля price:
            - Поле price містить ВИКЛЮЧНО грошову суму (число + валюта), знайдену в caption поста.
            - В price ОБОВ'ЯЗКОВО має бути число. Якщо числа немає — став порожній рядок.
            - Приклади правильних значень: "25 000 CZK/měsíc", "3 500 000 CZK", "150 000 €", "1 200 EUR/місяць"
            - Приклади НЕПРАВИЛЬНИХ значень: "rent", "sale", "оренда", "продаж", "квартира", "будинок", "дім", "byt", "dům", "apartment", "house"
            - НЕ пиши в price тип нерухомості (квартира/будинок/дім/byt) або тип угоди (оренда/продаж/rent/sale).
            - Якщо ціна відсутня в тексті — price має бути порожнім рядком "".

            4. Перекласти title, subtitle, location, body, tags та key_metrics на мови: {langs_list}
               Переклади мають бути якісними, з збереженням тону та маркетингової привабливості.

            МОВА БАЗОВОГО КОНТЕНТУ: УКРАЇНСЬКА (uk). Це головна та обов'язкова вимога.
            Переклади (translations) створюються на: {langs_list}.

            Відповідь має бути JSON-об'єктом з полями базової статті (УКРАЇНСЬКОЮ) та полем translations з перекладами на кожну мову.
            Якщо пост не є оголошенням — поверни null.
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
                "post_type": {
                    "type": "string",
                    "enum": ["rent", "sale"],
                    "description": "Тип объявления: rent (аренда) или sale (продажа). НЕ цена.",
                },
                "slug": {"type": "string"},
                "title": {"type": "string", "description": "Заголовок УКРАЇНСЬКОЮ мовою"},
                "subtitle": {"type": "string", "description": "Підзаголовок УКРАЇНСЬКОЮ мовою"},
                "location": {"type": "string", "description": "Локація УКРАЇНСЬКОЮ мовою"},
                "body": {"type": "string", "description": "Опис УКРАЇНСЬКОЮ мовою"},
                "price": {
                    "type": "string",
                    "description": (
                        "ТОЛЬКО денежная сумма с валютой из текста поста, например '25 000 CZK/měsíc' или '150 000 €'. "
                        "Пустая строка если цена не указана. "
                        "НЕ пиши сюда тип недвижимости (квартира/будинок/byt/dům) или тип сделки (rent/sale)."
                    ),
                },
                "price_on_request": {
                    "type": "boolean",
                    "description": "true только если price — пустая строка (цена не найдена в тексте).",
                },
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

        # send_messages returns Text.to_dict():
        #   {"value": <parsed JSON>, "annotations": [...]}
        # where <parsed JSON> is our schema wrapper:
        #   {"value": <article_data | null>}
        #
        # We need to unwrap BOTH levels to get the actual article data.

        # 1st unwrap: OpenAI Text wrapper → our schema response
        result = response
        if isinstance(result, dict) and "value" in result:
            result = result.get("value")

        # 2nd unwrap: our JSON schema nullable wrapper → actual data or None
        if isinstance(result, dict) and "value" in result:
            result = result.get("value")

        return result if isinstance(result, dict) else None
