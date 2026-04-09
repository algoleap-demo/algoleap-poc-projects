import httpx
import asyncio

async def debug():
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": "Bearer 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",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://algoleap.com",
        "X-Title": "IQ-EQ Agent Mesh POC"
    }
    payload = {
        "model": "google/gemma-4-31b-it:free",
        "messages": [{"role": "user", "content": "hi"}]
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"Status: {resp.status_code}")
            print(f"Text: {resp.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug())
