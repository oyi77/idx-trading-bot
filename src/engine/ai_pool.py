import asyncio
import google.generativeai as genai
from typing import List, Optional

class GeminiPool:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_index = 0
        
    def get_key(self) -> str:
        key = self.api_keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        return key

    async def generate_insight(self, prompt: str) -> Optional[str]:
        attempts = 0
        while attempts < len(self.api_keys):
            key = self.get_key()
            try:
                genai.configure(api_key=key)
                # Gunakan flash biar kenceng dan hemat token
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = await asyncio.to_thread(model.generate_content, prompt)
                if response and response.text:
                    return response.text
            except Exception as e:
                attempts += 1
                await asyncio.sleep(0.5)
        return None

import os

# Load dari .env
_keys_env = os.environ.get("GEMINI_KEYS", "")
KEYS = [k.strip() for k in _keys_env.split(",") if k.strip()]

if not KEYS:
    raise RuntimeError("GEMINI_KEYS not configured in .env")

ai_pool = GeminiPool(KEYS)
