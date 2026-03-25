"""Upstage Solar Embedding 래퍼."""

import time

from openai import OpenAI

from ingester.config import Config

# Upstage embedding-passage 최대 4000 토큰
# 한국어 실측: ~1.3 chars/token이므로 5000자로 절단
_MAX_CHARS = 5000


class Embedder:
    """Upstage Solar Embedding API 호출 (OpenAI 호환).

    - embed_batch / embed_single: 문서/청크 임베딩 (embedding-passage)
    - embed_query: 검색 쿼리 임베딩 (embedding-query)
    """

    def __init__(self, config: Config | None = None):
        cfg = config or Config.from_env()
        self.client = OpenAI(
            api_key=cfg.upstage_api_key,
            base_url=cfg.embedding_base_url,
        )
        self.model_passage = cfg.embedding_model  # "embedding-passage"
        self.model_query = "embedding-query"
        self.dimensions = cfg.embedding_dimensions

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """문서/청크 배치 임베딩 (embedding-passage)."""
        all_embeddings: list[list[float]] = []

        for text in texts:
            clean = _truncate(text)
            emb = self._call_api_single(clean, self.model_passage)
            all_embeddings.append(emb)

        return all_embeddings

    def embed_single(self, text: str) -> list[float]:
        """단일 문서/청크 임베딩 (embedding-passage)."""
        return self._call_api_single(_truncate(text), self.model_passage)

    def embed_query(self, text: str) -> list[float]:
        """검색 쿼리 임베딩 (embedding-query)."""
        return self._call_api_single(_truncate(text), self.model_query)

    def _call_api_single(
        self, text: str, model: str, max_retries: int = 3
    ) -> list[float]:
        """단일 텍스트 API 호출 + 지수 백오프 재시도."""
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    input=text,
                    model=model,
                )
                return response.data[0].embedding
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt
                print(f"  Embedding API error (retrying in {wait}s): {e}")
                time.sleep(wait)
        return []


def _truncate(text: str) -> str:
    """Upstage 4000토큰 제한 대응."""
    text = text.strip() if text.strip() else "empty"
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    return text
