import httpx
import asyncio
from config import settings


async def async_generate(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GEMINI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        )
        data = response.json()

        if "choices" not in data:
            error = data.get("error", {})
            raise ValueError(f"Groq error: {error.get('message', str(data))}")

        return data["choices"][0]["message"]["content"].strip()


def generate(prompt: str) -> str:
    return asyncio.run(async_generate(prompt))