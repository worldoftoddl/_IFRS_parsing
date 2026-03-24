-- K-IFRS 벡터 DB 스키마
CREATE EXTENSION IF NOT EXISTS vector;

-- 기준서 참조 테이블
CREATE TABLE IF NOT EXISTS standards (
    standard_id         TEXT PRIMARY KEY,
    standard_number     TEXT,
    title               TEXT NOT NULL,
    standard_type       TEXT NOT NULL,
    standard_family     TEXT NOT NULL,
    original_number     TEXT,
    base_authority      SMALLINT NOT NULL,
    last_amended_year   TEXT,
    components          TEXT[] NOT NULL,
    has_korean_additions BOOLEAN DEFAULT FALSE,
    korean_paragraph_count INTEGER DEFAULT 0,
    total_chunks        INTEGER DEFAULT 0,
    source_file         TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 청크 테이블 (검색 대상)
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id            TEXT PRIMARY KEY,
    standard_id         TEXT NOT NULL REFERENCES standards(standard_id),
    para_number         TEXT,
    component           TEXT NOT NULL,
    section_title       TEXT,
    authority           SMALLINT NOT NULL,
    content_text        TEXT NOT NULL,
    content_markdown    TEXT NOT NULL,
    embedding           vector(1536),
    char_count          INTEGER NOT NULL,
    token_estimate      INTEGER NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 각주 테이블
CREATE TABLE IF NOT EXISTS footnotes (
    footnote_id         SERIAL PRIMARY KEY,
    standard_id         TEXT NOT NULL REFERENCES standards(standard_id),
    footnote_number     INTEGER NOT NULL,
    content             TEXT NOT NULL,
    UNIQUE(standard_id, footnote_number)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_chunks_standard ON chunks(standard_id);
CREATE INDEX IF NOT EXISTS idx_chunks_component ON chunks(component);
CREATE INDEX IF NOT EXISTS idx_chunks_authority ON chunks(authority);

-- 기준서 식별용 요약 (Step 1)
CREATE TABLE IF NOT EXISTS standard_summaries (
    standard_id         TEXT PRIMARY KEY REFERENCES standards(standard_id),
    title               TEXT NOT NULL,
    scope_text          TEXT NOT NULL,
    scope_markdown      TEXT NOT NULL,
    embedding           vector(1536),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- BC/IE → 본문 문단 참조 링크 (Steps 3-4)
CREATE TABLE IF NOT EXISTS paragraph_links (
    link_id             SERIAL PRIMARY KEY,
    standard_id         TEXT NOT NULL REFERENCES standards(standard_id),
    source_chunk_id     TEXT NOT NULL,
    source_component    TEXT NOT NULL,
    source_para         TEXT,
    target_para_start   TEXT NOT NULL,
    target_para_end     TEXT,
    link_type           TEXT NOT NULL,
    UNIQUE(source_chunk_id, target_para_start, target_para_end)
);

CREATE INDEX IF NOT EXISTS idx_links_standard_target
    ON paragraph_links(standard_id, target_para_start);
CREATE INDEX IF NOT EXISTS idx_links_source_component
    ON paragraph_links(standard_id, source_component);

-- HNSW 벡터 인덱스 (임베딩 삽입 후 생성 권장)
-- CREATE INDEX idx_chunks_embedding ON chunks
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);
-- CREATE INDEX idx_summaries_embedding ON standard_summaries
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);
