"""Runtime configuration loaded from environment variables and .env."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    firms_map_key: str = ""
    firms_sources: list[str] = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
    india_bbox: tuple[float, float, float, float] = (68.0, 7.5, 97.0, 36.0)
    poll_interval_seconds: int = 600
    backfill_days: int = 90
    cluster_cell_deg: float = 0.02
    scorer_backend: Literal["heuristic", "xgboost"] = "heuristic"
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    offline_mode: bool = False
    worldcover_cache_dir: Path = Path("data/raw/worldcover")
    facility_match_radius_m: int = 2000
    llm_provider: Literal["auto", "ollama", "openai", "anthropic", "template"] = "auto"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    agnivani_env: Literal["development", "production", "staging"] = "development"
    cors_allow_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    agnivani_cors_allow_all: bool = False
    agnivani_api_token: str = ""
    cors_origins: list[str] | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        if self.agnivani_cors_allow_all:
            return ["*"]
        if self.cors_origins is not None:
            return self.cors_origins
        return [x.strip() for x in self.cors_allow_origins.split(",") if x.strip()]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [x.strip() for x in value.split(",") if x.strip()]
        return value

    @field_validator("firms_sources")
    @classmethod
    def supported_sources(cls, value: list[str]) -> list[str]:
        forbidden = {x for x in value if x not in {"VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"}}
        if forbidden:
            raise ValueError(f"unsupported FIRMS source(s): {sorted(forbidden)}")
        return value

    @model_validator(mode="after")
    def key_required_online(self):
        if not self.offline_mode and not self.firms_map_key:
            raise ValueError("FIRMS_MAP_KEY is required when OFFLINE_MODE=false; copy .env.example to .env")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
