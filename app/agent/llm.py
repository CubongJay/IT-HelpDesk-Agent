import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


def get_llm() -> BaseChatModel:
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    provider = os.getenv("LLM_PROVIDER", "openai")
    return init_chat_model(model=model, model_provider=provider, temperature=0)
