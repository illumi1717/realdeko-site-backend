import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class OpenAIAPI:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your environment or pass api_key explicitly."
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def create_agent(
        self,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Создаёт ассистента и возвращает его id."""
        resp = self.client.beta.assistants.create(
            name="Pipeline Agent",
            model=self.model,
            instructions=system_prompt,
            tools=tools or [],
            response_format=self._schema_to_response_format(response_schema),
        )
        return resp.id

    def send_messages(
        self,
        assistant_id: str,
        messages: List[Dict[str, str]],
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Шлёт сообщения ассистенту и ждёт завершения run.
        messages: [{"role": "user"|"assistant"|"system", "content": "..."}]
        Возвращает JSON-совместимый словарь при включённом schema.
        """
        thread = self.client.beta.threads.create(messages=messages)
        run = self.client.beta.threads.runs.create_and_poll(
            assistant_id=assistant_id,
            thread_id=thread.id,
            response_format=self._schema_to_response_format(response_schema),
        )

        last_msg = self.client.beta.threads.messages.list(thread_id=thread.id, limit=1).data[0]
        content_item = last_msg.content[0]
        if hasattr(content_item, "text"):
            return content_item.text.to_dict() 
        return content_item.to_dict()

    @staticmethod
    def _schema_to_response_format(schema: Optional[Dict[str, Any]]):
        if not schema:
            return None

        schema_with_flags = dict(schema)
        if schema_with_flags.get("type") == "object":
            schema_with_flags.setdefault("additionalProperties", False)
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema_with_flags.get("title", "response"),
                "schema": schema_with_flags,
                "strict": True,
            },
        }