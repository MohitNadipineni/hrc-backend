from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "HRC Backend"
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ragdemo"

    llm_provider: str = "offline"
    embedding_dim: int = 1536
    sharepoint_dir: str = "data/sharepoint"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_embedding_deployment: str = ""
    azure_chat_deployment: str = ""
    auth_mode: str = "dev"
    api_keys: dict[str, dict] = {}
    candidate_k: int = 20
    min_similarity: float = 0.30
    database_ro_url: str = "postgresql://chatbot_ro:change-me@localhost:5432/ragdemo"
    sql_max_rows: int = 200
    sql_timeout_ms: int = 5000


settings = Settings()