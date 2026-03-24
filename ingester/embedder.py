"""Upstage Solar Embedding 래퍼."""

import time

from openai import OpenAI

from ingester.config import Config


class Embedder:
    """Upstage Solar Embedding API 배치 호출 (OpenAI 호환)."""

    def __init__(self, config: Config | None = None):
        cfg = config or Config.from_env()
        self.client = OpenAI(
            api_key=cfg.upstage_api_key,
            base_url=cfg.embedding_base_url,
        )
        self.model = cfg.embedding_model
        self.dimensions = cfg.embedding_dimensions
        self.batch_size = cfg.batch_size

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 배치 임베딩. 긴 텍스트는 잘라냄."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            clean_batch = [self._truncate(t) for t in batch]
            embeddings = self._call_api(clean_batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    @staticmethod
    def _truncate(text: str, max_chars: int = 6000) -> str:
        """Upstage 4000토큰 제한 대응. 한국어 ~1.5chars/token 기준 6000자로 절단."""
        text = text.strip() if text.strip() else "empty"
        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    def embed_single(self, text: str) -> list[float]:
        """단일 텍스트 임베딩."""
        return self._call_api([text])[0]

    def _call_api(
        self, texts: list[str], max_retries: int = 3
    ) -> list[list[float]]:
        """API 호출 + 지수 백오프 재시도."""
        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.model,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt
                print(f"  Embedding API error: {e}, retrying in {wait}s...")
                time.sleep(wait)
        return []
