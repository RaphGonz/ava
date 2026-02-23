from pydantic_settings import BaseSettings
from pydantic import field_validator
import json


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://ava:ava@localhost:5432/ava"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "ava_memories"

    # Embedding
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_vector_dim: int = 384

    # Ollama
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_chat_model: str = "mistral"
    ollama_her_model: str = "dolphin-mistral"
    ollama_supervisor_model: str = "llama3.1:8b"

    # Agent
    agent_context_messages: int = 20
    supervisor_context_messages: int = 10
    safe_word_max_words: int = 4

    # Memory
    memory_min_fact_length: int = 40
    memory_recall_limit: int = 5

    # Her mode
    her_exit_keywords: list[str] = ["exit her", "back to jarvis", "stop"]
    her_inactivity_timeout_minutes: int = 30

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    jwt_refresh_token_expire_days: int = 7

    # ComfyUI Cloud
    comfyui_url: str = "https://cloud.comfy.org"
    comfyui_api_key: str = ""
    comfyui_submit_timeout: float = 30.0
    comfyui_poll_timeout: float = 300.0
    comfyui_poll_interval: float = 3.0
    comfyui_request_timeout: float = 10.0
    comfyui_download_timeout: float = 60.0
    comfyui_workflow_template: str = "qwen_default.json"
    comfyui_t2i_workflow_template: str = "qwen_t2i.json"

    # Prompt rewriter
    prompt_rewriter_model: str = "mistral"
    prompt_rewriter_max_tokens: int = 300

    # Image generation defaults
    image_max_width: int = 1024
    image_max_height: int = 1024
    image_default_width: int = 768
    image_default_height: int = 1024
    image_sampler_steps: int = 25
    image_cfg_scale: float = 7.0
    image_sampler_name: str = "euler_ancestral"
    image_scheduler: str = "normal"
    image_checkpoint_name: str = "sd_xl_base_1.0.safetensors"
    image_negative_prompt: str = "ugly, blurry, deformed, low quality"
    image_filename_prefix: str = "ava_gen"

    # Chat API defaults
    chat_history_default_limit: int = 50
    chat_sessions_default_limit: int = 20

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
