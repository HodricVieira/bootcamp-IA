from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    max_file_size: int = 10 * 1024 * 1024
    chunk_size: int = 1000
    chunk_overlap: int = 150
    max_search_results: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOCUMIND_")


settings = Settings()
