import os
import json
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

async def call_router(prompt: str, max_retries: int = 3):
    """
    Call OpenRouter with a prompt and return the parsed JSON response.
    Includes basic retry logic for network errors.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://algoleap.com",
        "X-Title": "IQ-EQ Agent Mesh POC",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise reasoning agent. Respond ONLY with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Clean up content in case there are markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                return json.loads(content)
                
            except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
                if attempt == max_retries - 1:
                    print(f"Error calling OpenRouter after {max_retries} attempts: {e}")
                    raise
                await asyncio.sleep(1 * (attempt + 1)) # Exponential backoff
    
    return None
