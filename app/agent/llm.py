import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel


def get_llm() -> BaseChatModel:
    model = os.getenv("LLM_MODEL", "kimi-k2.6")
    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "moonshot":
        return init_chat_model(
            model=model,
            model_provider="openai",
            api_key=os.getenv("MOONSHOT_API_KEY"),
            base_url="https://api.moonshot.ai/v1",
            temperature=1,
        )

    return init_chat_model(model=model, model_provider=provider, temperature=0)
