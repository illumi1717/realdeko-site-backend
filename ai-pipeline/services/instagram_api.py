import http.client
import json
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class InstagramAPI:
    def __init__(self, api_key: Optional[str] = None, host: str = "instagram120.p.rapidapi.com"):
        self.api_key = api_key or os.getenv("INSTAGRAM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "INSTAGRAM_API_KEY is not set. Add it to your environment or pass api_key explicitly."
            )
        self.host = host

    def get_posts(self, username: str, max_id: str = "") -> str:
        """
        Fetch posts for the given Instagram username via RapidAPI.
        Returns the raw JSON response as a string.
        """
        conn = http.client.HTTPSConnection(self.host)
        payload = json.dumps({"username": username, "maxId": max_id})

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
            "Content-Type": "application/json",
        }

        conn.request("POST", "/api/instagram/posts", payload, headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return json.loads(data.decode("utf-8"))