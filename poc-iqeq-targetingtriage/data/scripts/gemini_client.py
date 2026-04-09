import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional


class GeminiError(RuntimeError):
    pass


def _post_json(url: str, payload: dict, timeout_s: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise GeminiError(f"HTTP {e.code} from Gemini: {body}") from e
    except urllib.error.URLError as e:
        raise GeminiError(f"Network error calling Gemini: {e}") from e


def generate_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
    timeout_s: int = 60,
    max_retries: int = 3,
) -> str:
    """
    Minimal Gemini REST client (no external dependencies).
    Requires GEMINI_API_KEY in environment.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not set")

    configured_model = model or os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    def build_url(model_name: str) -> str:
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": system_prompt}]},
            {"role": "user", "parts": [{"text": user_prompt}]},
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }

    backoff_s = 1.5
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            data = _post_json(build_url(configured_model), payload, timeout_s)
            candidates = data.get("candidates") or []
            if not candidates:
                raise GeminiError(f"No candidates in Gemini response: {data}")
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text_chunks = [p.get("text", "") for p in parts if isinstance(p, dict)]
            text = "".join(text_chunks).strip()
            if not text:
                raise GeminiError(f"Empty text in Gemini response: {data}")
            return text
        except GeminiError as e:
            last_err = e
            msg = str(e)

            # If the configured model is unavailable, fall back to a stable alias.
            if "HTTP 404" in msg and "is not found for API version v1beta" in msg and configured_model != "gemini-flash-latest":
                configured_model = "gemini-flash-latest"
                continue

            # Basic retry for rate limits/transient server errors based on message.
            is_retryable = any(code in msg for code in ["HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504"])
            if attempt >= max_retries or not is_retryable:
                raise
            time.sleep(backoff_s)
            backoff_s *= 2

    raise GeminiError(f"Gemini call failed: {last_err}")

