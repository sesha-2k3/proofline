from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["anthropic", "bedrock", ""] = ""
    model_id: str = ""
    anthropic_api_key: str = ""
    aws_region: str = "us-east-1"
    max_upload_mb: int = 10
    rules_path: Path = REPO_ROOT / "rules" / "masshealth.yaml"
    samples_dir: Path = BACKEND_DIR / "samples"
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"

    @property
    def demo_mode(self) -> bool:
        return not self.llm_provider or not self.model_id


@lru_cache
def get_settings() -> Settings:
    return Settings()
