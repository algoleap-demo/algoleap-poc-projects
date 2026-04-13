import os
import json
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from pathlib import Path

env_path = Path(__file__).parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_core.prompts import PromptTemplate

LLM_SEMAPHORE = asyncio.Semaphore(3)


def get_model() -> BaseChatModel:
    """POC1 / general-purpose LLM (multi-provider). Not used for POC2 briefs."""
    if GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=GOOGLE_API_KEY,
            convert_system_message_to_human=True,
        )

    if OPENAI_API_KEY:
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

    if OPENROUTER_API_KEY:
        return ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    raise RuntimeError("No valid Online LLM API keys found in .env.")


def get_planning_model() -> BaseChatModel:
    """POC2 Account Brief Agent — OpenRouter only (POC2_Requirements_v3 §12)."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required for Account Planning (POC2). "
            "Set POC2_LLM_MODEL optionally (e.g. anthropic/claude-3.5-sonnet)."
        )
    model_name = os.getenv("POC2_LLM_MODEL", OPENROUTER_MODEL)
    return ChatOpenAI(
        model=model_name,
        api_key=OPENROUTER_API_KEY,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model_kwargs={"response_format": {"type": "json_object"}},
    )


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


@retry(
    stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def run_planning_chain(prompt_text: str, inputs: dict) -> dict:
    """Single-account brief + call plan JSON via OpenRouter."""
    async with LLM_SEMAPHORE:
        model = get_planning_model()
        prompt = PromptTemplate.from_template(prompt_text)
        chain = prompt | model
        response = await chain.ainvoke(inputs)
        content = response.content
        return _parse_json_content(content)
