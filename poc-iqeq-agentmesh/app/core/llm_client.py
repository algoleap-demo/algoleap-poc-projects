import os
import json
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

# Global semaphore to prevent rate limiting (Max 3 concurrent LLM calls)
LLM_SEMAPHORE = asyncio.Semaphore(3)

def get_model() -> BaseChatModel:
    """
    Factory to return the prioritized LangChain ChatModel.
    """
    if GOOGLE_API_KEY:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", 
            google_api_key=GOOGLE_API_KEY,
            convert_system_message_to_human=True
        )
    
    if OPENAI_API_KEY:
        return ChatOpenAI(
            model="gpt-4o-mini", 
            api_key=OPENAI_API_KEY,
            model_kwargs={"response_format": {"type": "json_object"}}
        )
        
    if GROQ_API_KEY:
        return ChatOpenAI(
            model="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    if OPENROUTER_API_KEY:
        return ChatOpenAI(
            model=OPENROUTER_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    raise RuntimeError("No valid Online LLM API keys found in .env.")
