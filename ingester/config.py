"""Stage 2 설정."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    db_url: str = ""
    upstage_api_key: str = ""
    embedding_model: str = "embedding-passage"
    embedding_dimensions: int = 4096
    embedding_base_url: str = "https://api.upstage.ai/v1"
    md_dir: str = "output/md"
    batch_size: int = 100  # Upstage 배치 제한이 OpenAI보다 작을 수 있음

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            db_url=os.environ.get("DATABASE_URL", "dbname=kifrs"),
            upstage_api_key=os.environ.get("UPSTAGE_API_KEY", ""),
            md_dir=os.environ.get("MD_DIR", "output/md"),
        )
