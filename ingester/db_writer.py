"""PostgreSQL 적재 모듈."""

from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from ingester.models import (
    ChunkRecord,
    FootnoteRecord,
    ParagraphLink,
    StandardRecord,
    StandardSummary,
)


class DBWriter:
    """PostgreSQL upsert 연산."""

    def __init__(self, db_url: str):
        self.conn = psycopg.connect(db_url, autocommit=True)
        register_vector(self.conn)

    def close(self):
        self.conn.close()

    def init_schema(self, schema_path: str = "schema.sql"):
        """schema.sql을 실행하여 테이블 생성."""
        sql = Path(schema_path).read_text(encoding="utf-8")
        self.conn.execute(sql)

    # ------------------------------------------------------------------
    # Standards
    # ------------------------------------------------------------------

    def upsert_standard(self, r: StandardRecord):
        self.conn.execute("""
            INSERT INTO standards (
                standard_id, standard_number, title, standard_type,
                standard_family, original_number, base_authority,
                last_amended_year, components, has_korean_additions,
                korean_paragraph_count, total_chunks, source_file
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (standard_id) DO UPDATE SET
                title=EXCLUDED.title, total_chunks=EXCLUDED.total_chunks,
                source_file=EXCLUDED.source_file
        """, (
            r.standard_id, r.standard_number, r.title, r.standard_type,
            r.standard_family, r.original_number, r.base_authority,
            r.last_amended_year, r.components, r.has_korean_additions,
            r.korean_paragraph_count, getattr(r, 'total_chunks', 0),
            r.source_file,
        ))

    # ------------------------------------------------------------------
    # Chunks
    # ------------------------------------------------------------------

    def upsert_chunks(
        self,
        records: list[ChunkRecord],
        embeddings: list[list[float]] | None = None,
    ):
        """청크 배치 upsert. embeddings가 None이면 NULL로 삽입."""
        with self.conn.cursor() as cur:
            for i, r in enumerate(records):
                emb = embeddings[i] if embeddings else None
                cur.execute("""
                    INSERT INTO chunks (
                        chunk_id, standard_id, para_number, component,
                        section_title, authority, content_text,
                        content_markdown, embedding, char_count, token_estimate
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content_text=EXCLUDED.content_text,
                        content_markdown=EXCLUDED.content_markdown,
                        embedding=EXCLUDED.embedding
                """, (
                    r.chunk_id, r.standard_id, r.para_number, r.component,
                    r.section_title, r.authority, r.content_text,
                    r.content_markdown, emb, r.char_count, r.token_estimate,
                ))

    # ------------------------------------------------------------------
    # Footnotes
    # ------------------------------------------------------------------

    def upsert_footnotes(self, records: list[FootnoteRecord]):
        with self.conn.cursor() as cur:
            for r in records:
                cur.execute("""
                    INSERT INTO footnotes (standard_id, footnote_number, content)
                    VALUES (%s,%s,%s)
                    ON CONFLICT (standard_id, footnote_number) DO UPDATE SET
                        content=EXCLUDED.content
                """, (r.standard_id, r.footnote_number, r.content))

    # ------------------------------------------------------------------
    # Standard Summaries
    # ------------------------------------------------------------------

    def upsert_summary(
        self,
        r: StandardSummary,
        embedding: list[float] | None = None,
    ):
        self.conn.execute("""
            INSERT INTO standard_summaries (
                standard_id, title, scope_text, scope_markdown,
                definitions_text, definitions_markdown, embedding
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (standard_id) DO UPDATE SET
                scope_text=EXCLUDED.scope_text,
                scope_markdown=EXCLUDED.scope_markdown,
                definitions_text=EXCLUDED.definitions_text,
                definitions_markdown=EXCLUDED.definitions_markdown,
                embedding=EXCLUDED.embedding
        """, (
            r.standard_id, r.title, r.scope_text, r.scope_markdown,
            r.definitions_text, r.definitions_markdown, embedding,
        ))

    # ------------------------------------------------------------------
    # Paragraph Links
    # ------------------------------------------------------------------

    def upsert_links(self, links: list[ParagraphLink]):
        with self.conn.cursor() as cur:
            for l in links:
                cur.execute("""
                    INSERT INTO paragraph_links (
                        standard_id, source_chunk_id, source_component,
                        source_para, target_para_start, target_para_end, link_type
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (source_chunk_id, target_para_start, target_para_end)
                    DO NOTHING
                """, (
                    l.standard_id, l.source_chunk_id, l.source_component,
                    l.source_para, l.target_para_start, l.target_para_end,
                    l.link_type,
                ))

    # ------------------------------------------------------------------
    # HNSW 인덱스
    # ------------------------------------------------------------------

    def create_vector_indexes(self):
        """벡터 인덱스 생성.

        pgvector 0.6은 HNSW/IVFFlat 모두 2000차원 제한.
        4096차원에서는 인덱스 없이 exact search 사용.
        standard_id 필터로 기준서당 ~234행만 스캔하므로 성능 충분.
        """
        print("Vector index: skipped (4096d exceeds pgvector 0.6 limit of 2000d)")
        print("Using exact search with standard_id filter (avg ~234 rows/standard)")
