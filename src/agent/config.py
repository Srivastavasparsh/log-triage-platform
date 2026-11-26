from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    github_token: str = ""
    github_repo: str = "Srivastavasparsh/log-triage-platform"
    logs_dir: str = "logs"
    max_retries: int = 2

    class Config:
        env_file = ".env"


settings = Settings()