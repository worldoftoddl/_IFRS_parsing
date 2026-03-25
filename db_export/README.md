# K-IFRS 벡터 DB 내보내기

## 내용물

| 파일 | 설명 |
|------|------|
| `kifrs_dump.pgdump` | PostgreSQL custom format 덤프 (265MB) |
| `schema.sql` | DB 스키마 정의 (참조용) |
| `docker-compose.yml` | pgvector Docker 설정 |

## DB 통계

- **내보내기 일자**: 2026-03-25
- **전체 크기**: 274 MB
- **임베딩**: Upstage Solar Embedding, 4096차원

| 테이블 | 행 수 | 크기 | 설명 |
|--------|-------|------|------|
| `standards` | 63 | 56 KB | 기준서 메타데이터 |
| `chunks` | 14,762 | 261 MB | 검색 대상 청크 + embedding vector(4096) |
| `standard_summaries` | 63 | 2.3 MB | 기준서 식별용 요약 + embedding vector(4096) |
| `footnotes` | - | 264 KB | 각주 |
| `paragraph_links` | - | 824 KB | BC/IE → 본문 문단 참조 링크 |

## 복원 방법

### 1. PostgreSQL + pgvector 준비

```bash
# docker-compose.yml을 사용하여 pgvector 컨테이너 기동
docker compose up -d
```

컨테이너 접속 정보:
- Host: `localhost:5432`
- DB: `kifrs`
- User: `kifrs`
- Password: `kifrs`

### 2. DB 복원

```bash
# 컨테이너 내부에서 복원
docker compose exec db pg_restore -U kifrs -d kifrs /path/to/kifrs_dump.pgdump

# 또는 로컬 psql이 있는 경우
PGPASSWORD=kifrs pg_restore -h localhost -U kifrs -d kifrs kifrs_dump.pgdump
```

### 3. 복원 확인

```bash
PGPASSWORD=kifrs psql -h localhost -U kifrs -d kifrs -c "\dt+"
PGPASSWORD=kifrs psql -h localhost -U kifrs -d kifrs -c "SELECT count(*) FROM chunks;"
```

## 검색 사용법

2단계 벡터 검색:

1. **Step 1** — `standard_summaries`에서 쿼리와 유사한 기준서 식별 (cosine similarity)
2. **Step 2** — 해당 기준서의 `chunks`에서 authority=1 문단 검색

임베딩 모델:
- 문서 적재: `embedding-passage` (Upstage Solar)
- 검색 쿼리: `embedding-query` (Upstage Solar)
- API: `https://api.upstage.ai/v1` (OpenAI 호환)

## 스키마 ERD

```
standards (63)
  ├── chunks (14,762)        — standard_id FK
  ├── standard_summaries (63) — standard_id FK
  ├── footnotes              — standard_id FK
  └── paragraph_links        — standard_id FK
                               source_chunk_id → chunks 참조
```
