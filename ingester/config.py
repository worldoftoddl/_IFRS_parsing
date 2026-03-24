"""Stage 2 설정."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    db_url: str = ""
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    md_dir: str = "output/md"
    batch_size: int = 500

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            db_url=os.environ.get("DATABASE_URL", "postgresql://localhost:5432/kifrs"),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            md_dir=os.environ.get("MD_DIR", "output/md"),
        )
