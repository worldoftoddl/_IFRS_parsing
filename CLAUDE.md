# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

K-IFRS(한국채택국제회계기준) 원문 .docx 파일을 **구조 보존 마크다운**으로 변환하고, 이를 벡터 DB에 적재하여 검색하는 2단계 파이프라인 프로젝트.

- **Stage 1** (`convert.py` + `converter/`): docx → 구조 보존 마크다운 (사람이 검수 가능한 중간 산출물)
- **Stage 2** (`ingest.py` + `ingester/`): 구조 보존 마크다운 → 청크 + 메타데이터 → PostgreSQL+pgvector 적재
- **검색**: `search_test.ipynb` — 2단계 벡터 검색 (기준서 식별 → 문단 검색)
- **관련 프로젝트**: 기존 파싱/임베딩/검색 코드 → `/home/shin/Home/Study/_database/`

## 저장소 구조

```
├── convert.py              ← Stage 1 CLI (docx → 마크다운)
├── converter/
│   ├── __init__.py
│   ├── models.py           ← IR 데이터클래스 (FormattedRun, AuthorityMarker 등)
│   ├── docx_parser.py      ← docx → IR 파서 (bold/italic, 각주, 권위 마커 추출)
│   └── md_renderer.py      ← IR → 구조 보존 마크다운 렌더러
├── ingest.py               ← Stage 2 CLI (마크다운 → 벡터 DB)
├── ingester/
│   ├── __init__.py
│   ├── config.py           ← Config 데이터클래스 (DB URL, Upstage API 키 등)
│   ├── models.py           ← Stage 2 데이터 모델 (StandardRecord, ChunkRecord 등)
│   ├── md_parser.py        ← 구조 보존 마크다운 → 청크 파서
│   ├── chunk_splitter.py   ← 초과 청크(4000토큰+) 분할
│   ├── link_extractor.py   ← BC/IE → 본문 문단 참조 링크 추출
│   ├── summary_builder.py  ← 기준서 식별용 요약 (목적+적용범위+정의) 생성
│   ├── embedder.py         ← Upstage Solar Embedding 래퍼 (passage/query 분리)
│   └── db_writer.py        ← PostgreSQL+pgvector 적재
├── schema.sql              ← DB 스키마 (standards, chunks, footnotes, paragraph_links, standard_summaries)
├── docker-compose.yml      ← pgvector/pgvector:pg17 (로컬 DB)
├── search_test.ipynb       ← 2단계 벡터 검색 테스트 노트북
├── pyproject.toml          ← 프로젝트 설정
├── .env                    ← 환경변수 (UPSTAGE_API_KEY 등, .gitignore)
├── IFRS_docx/              ← K-IFRS 원문 .docx 파일들 (63개)
│   ├── IAS_10XX/           ← IAS 계열 (IASC 발행 기준서) — 25개
│   ├── IFRS_11XX/          ← IFRS 계열 (IASB 발행 기준서) — 16개
│   ├── SIC_20XX/           ← SIC 해석서 (IASC 해석위원회) — 4개
│   ├── IFRIC_21XX/         ← IFRIC 해석서 (IASB 해석위원회) — 15개
│   └── 개념체계/            ← 개념체계 + 실무서 — 3개
├── output/md/              ← 생성된 마크다운 파일 63개 (.gitignore)
├── output/search_chunks/   ← 검수용 JSON 내보내기 (.gitignore)
└── how_to_read_IFRS.md     ← IFRS 3단 구조, 권위 수준, 벡터 DB 메타데이터 설계 참조 문서
```

## 빌드 & 실행

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .   # python-docx, lxml, openai, psycopg[binary], pgvector, python-dotenv, sentence-transformers

# --- Stage 1: docx → 마크다운 ---
python convert.py                    # 전체 변환 (63개)
python convert.py --single "IFRS_docx/IAS_10XX/시행중_K-IFRS_제1024호...docx"
python convert.py --dry-run          # 파싱+통계만

# --- Stage 2: 마크다운 → 벡터 DB ---
docker compose up -d                 # PostgreSQL+pgvector 기동
python ingest.py                     # 전체 (파싱+임베딩+DB 적재)
python ingest.py --parse-only        # 파싱 통계만
python ingest.py --skip-embedding    # DB 삽입 (임베딩 NULL)
python ingest.py --export-json       # JSON 내보내기 (검수용)
python ingest.py --single "K-IFRS 1115"  # 단일 기준서

# --- 환경변수 (.env) ---
# UPSTAGE_API_KEY=...
# DATABASE_URL=dbname=kifrs (기본값)
```

## Stage 1 파이프라인 아키텍처

### IR(Intermediate Representation) 모델 (`converter/models.py`)

docx를 파싱하면 다음 IR 요소들의 리스트로 변환된다:

- `MetaInfo` — 기준서 메타데이터 (파일명 기반)
- `SectionHeader` — 섹션 헤더 + section_type (main/ag/bc/ie/definitions/transition)
- `AuthorityMarker` — "이 부록은 기준서의 일부를 구성한다" 등 권위 선언 문구
- `NumberedParagraph` — 번호 문단 + FormattedRun(bold/italic) + 각주 참조
- `ContinuationText` — 번호 없는 이어지는 텍스트
- `ContentTable` — 표
- `SubItem` — 호/목 (⑴⑵⑶, ㈎㈏㈐)
- `Footnote` — 각주 (footnotes.xml에서 추출)

### 구조 보존 마크다운 출력 포맷 (`converter/md_renderer.py`)

```markdown
---
standard_id: "K-IFRS 1115"
standard_number: "1115"
title: "고객과의 계약에서 생기는 수익"
---

# K-IFRS 1115 고객과의 계약에서 생기는 수익

## 본 문
<!-- component: main | authority: 1 -->

**1	핵심 원칙 문단 (전체 bold = 원칙)**
<!-- para: 1 | bold_para -->

2	일반 문단, *정의 용어*는 italic
<!-- para: 2 -->

한2.1	한국 고유 추가사항
<!-- para: 한2.1 | korean_addition -->

## [결론도출근거]
<!-- component: bc | authority: 4 -->

*이 결론도출근거는 기준서의 일부를 구성하는 것은 아니다.*
<!-- authority_declaration: non-authoritative -->

---
[^1]: 각주 내용
```

**메타데이터 인코딩:**
- YAML 프론트매터 → 기준서 메타데이터
- `<!-- component: X | authority: N -->` → 섹션별 컴포넌트/권위 수준
- `<!-- para: X | bold_para | korean_addition -->` → 문단 메타데이터
- `<!-- authority_declaration: authoritative/non-authoritative -->` → 권위 선언
- `**bold**` → 핵심 원칙 문단 / `*italic*` → 정의 용어 참조
- `[^N]` → 각주

## Stage 2 파이프라인 아키텍처

### 처리 흐름

```
output/md/*.md
  → md_parser.parse_markdown_file()    → StandardRecord + ChunkRecord[] + FootnoteRecord[]
  → chunk_splitter.split_oversized()   → 4000토큰 초과 청크 분할
  → link_extractor.extract_links()     → ParagraphLink[] (BC/IE → 본문 참조)
  → summary_builder.build_summary()    → StandardSummary (목적+적용범위+정의)
  → embedder.embed_batch/single()      → 벡터 임베딩
  → db_writer.upsert_*()               → PostgreSQL+pgvector 적재
```

### 임베딩 (`ingester/embedder.py`)

- **Upstage Solar Embedding** (OpenAI 호환 API)
- **passage/query 모델 분리**: 문서 적재 시 `embedding-passage`, 검색 쿼리 시 `embedding-query`
- 차원: 4096, 최대 4000토큰 (한국어 ~5000자 절단)

### DB 스키마 (`schema.sql`)

| 테이블 | 용도 |
|--------|------|
| `standards` | 기준서 메타데이터 (63개) |
| `chunks` | 검색 대상 청크 (번호 문단 단위, embedding vector(4096)) |
| `standard_summaries` | 기준서 식별용 요약 (목적+적용범위+정의, embedding vector(4096)) |
| `footnotes` | 각주 |
| `paragraph_links` | BC/IE → 본문 문단 참조 링크 |

- 정의(definitions) 청크는 `standard_summaries`에 통합되어 별도 검색 대상에서 제외

### 검색 전략 (`search_test.ipynb`)

2단계 벡터 검색:
1. **Step 1** — `standard_summaries` 테이블에서 쿼리와 가장 유사한 기준서 식별
2. **Step 2** — 식별된 기준서의 `chunks` 테이블에서 Level 1(Authoritative) 문단 검색

## K-IFRS 번호 체계 (2×2 매트릭스)

첫째 자리가 기준서(1) vs 해석서(2), 둘째 자리가 구(舊)기구(0) vs 신(新)기구(1)를 구분한다.

|  | 구(舊) IASC (~2000) | 신(新) IASB (2001~) |
|---|---|---|
| **기준서** | 제**10**XX호 (IAS) | 제**11**XX호 (IFRS) |
| **해석서** | 제**20**XX호 (SIC) | 제**21**XX호 (IFRIC) |

IAS와 IFRS는 체계 설계 철학이 다르다. IAS는 선택적 회계처리를 폭넓게 허용, IFRS는 선택지를 줄이는 방향. 문서 구조(부록 편제, AG 분량 등)도 상당히 다를 수 있어 파서 설계 시 감안 필요.

## 핵심 도메인 지식

### 권위 수준 5단계 (벡터 DB 메타데이터 설계 기준)

| Level | 구성요소 | 검색 우선순위 |
|-------|---------|-------------|
| 1 (Authoritative) | 기준서 본문, 부록A(정의), 부록B(적용지침), 부록C(경과규정), IFRIC/SIC 해석서 | 최상위 |
| 2 (Quasi-authoritative) | IFRIC 안건결정 | 상위 |
| 3 (Framework) | 개념체계 | 중위 |
| 4 (Non-authoritative) | 결론도출근거(BC), 적용사례(IE), 이행지침(IG) | 하위 |
| 5 (External) | US GAAP, Big 4 출판물 | 최하위 |

### 권위 수준 자동 태깅 기준 (K-IFRS 한국어 표현)

.docx 파일 내에서 아래 패턴을 정규식 매칭하여 `authority_level` 메타데이터를 기계적으로 분류할 수 있다.

| K-IFRS 한국어 표현 | 영문 원문 | 판정 |
|---|---|---|
| **"이 부록은 이 기준서의 일부를 구성한다"** | "integral part of the Standard" | **Authoritative (Level 1)** |
| **"이 기준서의 다른 부분과 동등한 권위를 지니고 있다"** | "equal authority" | **Authoritative 확인** |
| **"이 기준서의 일부를 구성하는 것은 아니다"** | "not part of the Standard" | **Non-authoritative (Level 4)** |
| **"모든 문단에는 동등한 권위가 부여되어 있다"** | "All paragraphs have equal authority" | **서문 포괄 선언** |

실제 검색 결과: 긍정 표현 45건, 부정 표현 88건 확인됨.

### K-IFRS 고유 요소

- "한" 접두어 문단(예: 한82.1): 한국 고유 추가 요구사항 (carve-in). `is_korean_addition` 메타데이터로 태깅
- K-IFRS는 IFRS를 무수정 번역 채택, carve-out 없음. 추가 표시·공시 요구사항만 존재
- 이중 질의회신 체계: 권위 순서 KASB 정규 > KASB 신속 > FSS 질의회신

## .docx 파일 접근 시 유의사항

- .docx 내부 경로가 Windows 스타일 백슬래시 (`word\document.xml`)로 되어 있음. `_open_docx()`에서 자동 수정
- 파일명에 한글·괄호·공백이 포함되어 있어 shell 명령어 시 이스케이프 필요
- 문단 번호는 `w:numPr`이 아닌 **텍스트에 직접 포함**되어 있음 (TAB 구분)
- 각주는 python-docx가 직접 지원하지 않으므로 lxml로 `word/footnotes.xml` 파싱

## 관련 프로젝트

기존 파싱 파이프라인, 임베딩, 검색 코드: `/home/shin/Home/Study/_database/`
- `pipeline/docx_parser.py` — 이 저장소의 `converter/docx_parser.py`의 원본 포크 소스
- `pipeline/docx_chunker.py` — Stage 2 청킹 설계 참조
