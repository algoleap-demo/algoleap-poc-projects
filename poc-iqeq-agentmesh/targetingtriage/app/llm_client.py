import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.constants import GEMINI_MODEL, OPENAI_MODEL, GROQ_MODEL
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

# Global semaphore to prevent rate limiting (Max 3 concurrent LLM calls)
LLM_SEMAPHORE = asyncio.Semaphore(3)

def is_free_tier() -> bool:
    """
    Returns True if the current model is a free-tier model on OpenRouter.
    """
    return ":free" in OPENROUTER_MODEL.lower()

def get_model(json_mode: bool = False) -> BaseChatModel:
    """
    Factory to return the prioritized LangChain ChatModel.
    """
    model_kwargs = {}
    if json_mode:
        model_kwargs["response_format"] = {"type": "json_object"}

    if GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL, 
            google_api_key=GOOGLE_API_KEY,
            convert_system_message_to_human=True
        )
    
    if OPENAI_API_KEY:
        return ChatOpenAI(
            model=OPENAI_MODEL, 
            api_key=OPENAI_API_KEY,
            model_kwargs=model_kwargs
        )
        
    if GROQ_API_KEY:
        return ChatOpenAI(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            model_kwargs=model_kwargs
        )

    if OPENROUTER_API_KEY and "sk-or-v1" in OPENROUTER_API_KEY:
        return ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=2500, # Optimized for credit-constrained sessions
            model_kwargs=model_kwargs
        )

    raise RuntimeError("No valid Online LLM API keys found in .env.")

async def call_router(prompt: str):
    """
    Legacy-compatible wrapper that now uses the LangChain factory.
    """
    model = get_model(json_mode=True)
    # LangChain invoke returns a BaseMessage, we extract the content
    response = await model.ainvoke(prompt)
    try:
        return json.loads(response.content)
    except Exception as e:
        # Fallback if the model didn't strictly return JSON
        print(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError(f"LLM did not return valid JSON: {response.content}")
