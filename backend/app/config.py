from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://urbanest:urbanest@localhost:5432/urbanest"
    redis_url: str = "redis://localhost:6379/0"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:0.5b"
    ollama_num_thread: int = 4
    ollama_num_ctx: int = 2048
    enable_ollama_chat: bool = False
    enable_ollama_search_summaries: bool = False
    scraping_delay_seconds: int = 1
    enable_live_scraping: bool = True
    enable_web_context: bool = True
    enable_general_web_search: bool = True
    web_search_max_results: int = 4
    web_search_endpoint: str = "https://duckduckgo.com/html/"
    allowed_web_domains: str = "fincaraiz.com.co,metrocuadrado.com,olx.com.co,facebook.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
