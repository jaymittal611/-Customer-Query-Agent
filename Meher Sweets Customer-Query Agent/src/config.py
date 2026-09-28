import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class AppSettings(BaseModel):
    # Ollama OpenAI-compatible endpoint configs
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "ollama")
    llm_model: str = os.getenv("LLM_MODEL", "llama3.1:8b")

    # Operational settings
    temperature: float = 0.0
    max_steps: int = 4                    # At most 4 model calls per customer message
    rupee_to_dollar_rate: float = 100.0  # Specification constant
    max_reply_chars: int = 1200          # 1 to 1200 characters limit
    is_local_model: bool = True          # If True, reports 0 cost per spec

config = AppSettings()