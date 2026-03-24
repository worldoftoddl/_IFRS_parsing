"""Stage 2 데이터 모델."""

from dataclasses import dataclass


@dataclass
class StandardRecord:
    """기준서 메타데이터 (프론트매터에서 추출)."""

    standard_id: str
    standard_number: str | None
    title: str
    standard_type: str
    standard_family: str
    original_number: str | None
    base_authority: int
    last_amended_year: str | None
    components: list[str]
    has_korean_additions: bool
    korean_paragraph_count: int
    source_file: str


@dataclass
class ChunkRecord:
    """하나의 검색 단위 (번호 문단 + 호/목 + 연속 텍스트)."""

    chunk_id: str
    standard_id: str
    para_number: str | None
    component: str
    section_title: str | None
    authority: int
    content_text: str       # 임베딩용 plain text
    content_markdown: str   # LLM 컨텍스트용 원본
    char_count: int = 0
    token_estimate: int = 0


@dataclass
class FootnoteRecord:
    """각주."""

    standard_id: str
    footnote_number: int
    content: str


@dataclass
class ParagraphLink:
    """BC/IE → 본문 문단 참조 링크."""

    standard_id: str
    source_chunk_id: str
    source_component: str       # 'bc' | 'ie'
    source_para: str | None
    target_para_start: str
    target_para_end: str | None
    link_type: str              # 'section_heading' | 'body_reference'


@dataclass
class StandardSummary:
    """기준서 식별용 요약 (목적 + 적용범위)."""

    standard_id: str
    title: str
    scope_text: str             # 임베딩용 plain text
    scope_markdown: str         # LLM 컨텍스트용 원본
