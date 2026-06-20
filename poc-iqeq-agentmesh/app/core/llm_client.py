import os
import re
import json
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from pathlib import Path

env_path = Path(__file__).parents[2] / ".env"
load_dotenv(dotenv_path=env_path)


def _reload_dotenv() -> None:
    """Re-read .env so key edits apply without restarting the interpreter."""
    load_dotenv(dotenv_path=env_path, override=True)


def openrouter_api_key() -> str:
    """Fresh OpenRouter key: reloads .env, strips whitespace and wrapping quotes."""
    _reload_dotenv()
    raw = os.getenv("OPENROUTER_API_KEY") or ""
    return raw.strip().strip('"').strip("'")


def _openrouter_base_url() -> str:
    u = (os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").strip().rstrip(
        "/"
    )
    return u


def _openrouter_default_headers() -> dict[str, str]:
    """Headers OpenRouter documents for attribution (may help some account/key edge cases)."""
    _reload_dotenv()
    referer = (
        os.getenv("OPENROUTER_HTTP_REFERER")
        or os.getenv("OPENROUTER_SITE_URL")
        or "http://127.0.0.1:8000"
    ).strip()
    title = (
        os.getenv("OPENROUTER_APP_TITLE")
        or os.getenv("X_OPENROUTER_TITLE")
        or "IQ-EQ-Unified-Agent-Mesh"
    ).strip()
    return {
        "HTTP-Referer": referer,
        "X-OpenRouter-Title": title,
    }


def _openrouter_chat_client_kwargs(api_key: str) -> dict:
    return {
        "api_key": api_key,
        "base_url": _openrouter_base_url(),
        "default_headers": _openrouter_default_headers(),
    }


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

from tenacity import retry, stop_after_attempt, wait_exponential, RetryError as TenacityRetryError
from langchain_core.prompts import PromptTemplate

LLM_SEMAPHORE = asyncio.Semaphore(3)


def _is_openrouter_key_shape(value: str | None) -> bool:
    """OpenRouter keys must not be sent to api.openai.com (common .env mistake)."""
    if not value:
        return False
    v = value.strip()
    return v.startswith("sk-or-v1-") or v.startswith("sk-or-")


def get_model() -> BaseChatModel:
    """POC1 / general-purpose LLM (multi-provider). Not used for POC2 briefs.

    Order: Google → OpenAI (platform.openai.com) → Groq → OpenRouter.
    If you only use OpenRouter, leave OPENAI_API_KEY unset so this reaches OpenRouter.
    """
    if GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=GOOGLE_API_KEY,
            convert_system_message_to_human=True,
        )

    if OPENAI_API_KEY and not _is_openrouter_key_shape(OPENAI_API_KEY):
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    if GROQ_API_KEY:
        return ChatOpenAI(
            model="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    key = openrouter_api_key()
    if key:
        model_id = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        return ChatOpenAI(
            model=model_id,
            model_kwargs={"response_format": {"type": "json_object"}},
            **_openrouter_chat_client_kwargs(key),
        )

    raise RuntimeError("No valid Online LLM API keys found in .env.")


def get_planning_model(*, json_mode: bool = True) -> BaseChatModel:
    """POC2 Account Brief Agent — OpenRouter only (POC2_Requirements_v3 §12)."""
    key = openrouter_api_key()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required for Account Planning (POC2). "
            "Set POC2_LLM_MODEL optionally (e.g. anthropic/claude-3.5-sonnet)."
        )
    model_name = os.getenv("POC2_LLM_MODEL") or os.getenv(
        "OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"
    )
    mk: dict = {"response_format": {"type": "json_object"}} if json_mode else {}
    return ChatOpenAI(
        model=model_name,
        model_kwargs=mk,
        **_openrouter_chat_client_kwargs(key),
    )


def format_chain_failure(exc: BaseException) -> str:
    """Readable message for UI / logs; unwraps tenacity RetryError when present."""
    e: BaseException | None = exc
    for _ in range(6):
        if e is None:
            break
        if isinstance(e, TenacityRetryError):
            inner = None
            la = getattr(e, "last_attempt", None)
            if la is not None:
                try:
                    inner = la.exception()
                except Exception:
                    inner = None
            if inner is not None:
                e = inner
                continue
        if e.__cause__ is not None:
            e = e.__cause__
            continue
        if e.__context__ is not None and type(e).__name__ == "RetryError":
            e = e.__context__
            continue
        break
    if e is None:
        return "LLM request failed (unknown error)"
    msg = str(e).strip()
    if not msg or msg == "RetryError[]":
        return repr(e)
    return msg


def _exception_chain(exc: BaseException) -> list[BaseException]:
    """Flatten __cause__ / __context__ / tenacity last_attempt for classification."""
    out: list[BaseException] = []
    seen: set[int] = set()
    e: BaseException | None = exc
    for _ in range(12):
        if e is None or id(e) in seen:
            break
        seen.add(id(e))
        out.append(e)
        if isinstance(e, TenacityRetryError):
            la = getattr(e, "last_attempt", None)
            inner = None
            if la is not None:
                try:
                    inner = la.exception()
                except Exception:
                    inner = None
            e = inner or e.__cause__ or e.__context__
            continue
        e = e.__cause__ or e.__context__
    return out


def explain_llm_error(exc: BaseException) -> tuple[str, str]:
    """Stable error_code and a short user-facing sentence (dashboards, HTTP detail)."""
    chain = _exception_chain(exc)
    blob = " ".join(str(x).lower() for x in chain)
    tnames = " ".join(type(x).__name__ for x in chain)

    sc = None
    for e in chain:
        sc = getattr(e, "status_code", None)
        if sc is not None:
            break
    if sc is None:
        m = re.search(r"\b(401|403|429|502|503|504)\b", blob)
        if m:
            sc = int(m.group(1))

    if sc in (401, 403):
        if "user not found" in blob:
            return (
                "AUTH",
                "OpenRouter responded with «User not found»: your API key is not tied to an OpenRouter "
                "account (typo, revoked key, or a key from another provider). Create a new key at "
                "https://openrouter.ai/keys (must start with sk-or-v1-…), set OPENROUTER_API_KEY in .env, "
                "and ensure OPENROUTER_BASE_URL is https://openrouter.ai/api/v1 unless you use a proxy.",
            )
        return (
            "AUTH",
            "The LLM provider rejected authentication. Check OPENROUTER_API_KEY and model access.",
        )
    if sc == 429:
        if "free-models-per-day" in blob or "add 10 credits" in blob:
            return (
                "RATE_LIMIT",
                "OpenRouter free-model daily quota is exhausted. Add credits at openrouter.ai/credits "
                "(unlocks more free-tier requests) or set OPENROUTER_MODEL / POC2_LLM_MODEL to a paid model.",
            )
        return (
            "RATE_LIMIT",
            "The provider rate-limited this workspace. Wait briefly and retry.",
        )
    if sc in (502, 503, 504):
        return (
            "PROVIDER_UNAVAILABLE",
            "The LLM provider returned a temporary error. Retry in a moment or try another model.",
        )

    if "timeout" in blob or "Timeout" in tnames or "ReadTimeout" in tnames:
        return (
            "TIMEOUT",
            "The LLM request timed out. Check your network; if it persists, try a lighter model.",
        )
    if any(x in blob for x in ("connection reset", "connection refused", "connecterror", "connection error", "network is unreachable", "name or service not known")):
        return (
            "CONNECTION",
            "Could not reach the LLM API. Check internet, VPN, firewall, and OPENROUTER_BASE_URL.",
        )
    if "openrouter_api_key" in blob or "api key" in blob or "invalid api key" in blob or "incorrect api key" in blob:
        return (
            "AUTH",
            "API key or authentication problem. Verify OPENROUTER_API_KEY in your .env file.",
        )
    if "jsondecodeerror" in blob or ("json" in blob and ("parse" in blob or "expecting" in blob)):
        return (
            "BAD_JSON",
            "The model returned text that was not valid JSON. Retry or switch POC2/POC3 model.",
        )
    if "empty llm response" in blob:
        return (
            "EMPTY_RESPONSE",
            "The model returned an empty reply. Retry or change model.",
        )
    if "retryerror" in blob or "openrouter planning chain failed" in blob:
        return (
            "LLM_RETRIES_EXHAUSTED",
            "Several LLM attempts failed in a row. See the technical summary for the last errors.",
        )
    return (
        "UNKNOWN",
        "An unexpected error occurred while calling the model. Check server logs for the full traceback.",
    )


def error_detail_for_http(exc: BaseException) -> dict:
    """Structured FastAPI `detail` for 502/500-style responses (JSON object)."""
    code, user_msg = explain_llm_error(exc)
    return {
        "error_code": code,
        "user_message": user_msg,
        "technical_summary": format_chain_failure(exc)[:2000],
    }


def _parse_json_content(content: str) -> dict:
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


@retry(
    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def run_standard_chain(prompt_text: str, inputs: dict) -> dict:
    async with LLM_SEMAPHORE:
        model = get_model()
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | model
        try:
            response = await chain.ainvoke(inputs)
            content = response.content
            return _parse_json_content(content)
        except Exception as e:
            print(f"!!! LLM Error in run_standard_chain: {str(e)}")
            if "content" in locals():
                return {"raw_text": content}
            raise e


async def run_planning_chain(prompt_text: str, inputs: dict) -> dict:
    """Single-account brief + call plan JSON via OpenRouter.

    Retries are implemented here (not via tenacity) so failures surface as
    RuntimeError with the last causes — never as opaque RetryError to callers.
    """
    prompt = PromptTemplate.from_template(prompt_text)
    all_errors: list[str] = []
    backoff_sec = [0, 2, 4, 10, 20]
    for attempt in range(5):
        if attempt > 0:
            await asyncio.sleep(backoff_sec[attempt])
        round_errors: list[str] = []
        async with LLM_SEMAPHORE:
            for json_mode in (True, False):
                try:
                    model = get_planning_model(json_mode=json_mode)
                    chain = prompt | model
                    response = await chain.ainvoke(inputs)
                    content = response.content
                    if content is None or not str(content).strip():
                        raise ValueError("Empty LLM response")
                    return _parse_json_content(str(content))
                except Exception as e:
                    round_errors.append(f"try={attempt + 1} json_mode={json_mode}: {e}")
                    continue
        all_errors.extend(round_errors)
    raise RuntimeError(
        "OpenRouter planning chain failed after retries: "
        + (" | ".join(all_errors[-6:]) if all_errors else "unknown error")
    )


def get_poc3_campaign_model(*, json_mode: bool = True) -> BaseChatModel:
    """POC3 Campaign Brief Agent — OpenRouter only (POC3_Requirements_v3 §12)."""
    key = openrouter_api_key()
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required for POC3 campaign briefs. "
            "Set POC3_LLM_MODEL optionally."
        )
    model_name = os.getenv("POC3_LLM_MODEL") or os.getenv(
        "OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"
    )
    mk: dict = {"response_format": {"type": "json_object"}} if json_mode else {}
    return ChatOpenAI(
        model=model_name,
        temperature=0.3,
        max_tokens=800,
        model_kwargs=mk,
        **_openrouter_chat_client_kwargs(key),
    )


async def run_poc3_campaign_chain(prompt_text: str, inputs: dict) -> dict:
    """One cluster campaign brief JSON via OpenRouter (retries here, not tenacity — avoids RetryError)."""
    prompt = PromptTemplate.from_template(prompt_text)
    all_errors: list[str] = []
    backoff_sec = [0, 2, 4, 8, 16]
    for attempt in range(5):
        if attempt > 0:
            await asyncio.sleep(backoff_sec[attempt])
        round_errors: list[str] = []
        async with LLM_SEMAPHORE:
            for json_mode in (True, False):
                try:
                    model = get_poc3_campaign_model(json_mode=json_mode)
                    chain = prompt | model
                    response = await chain.ainvoke(inputs)
                    content = response.content
                    if content is None or not str(content).strip():
                        raise ValueError("Empty LLM response")
                    return _parse_json_content(str(content))
                except Exception as e:
                    round_errors.append(
                        f"try={attempt + 1} json_mode={json_mode}: {e}"
                    )
                    continue
        all_errors.extend(round_errors)
    raise RuntimeError(
        "POC3 campaign LLM failed after retries: "
        + (" | ".join(all_errors[-6:]) if all_errors else "unknown error")
    )
