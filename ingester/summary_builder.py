"""기준서 식별용 요약 생성 (목적 + 적용범위 + 정의)."""

from ingester.models import ChunkRecord, StandardRecord, StandardSummary

_SCOPE_TITLES = {"목적", "적용범위", "적용", "제1장 목적", "목적과 적용범위"}


def build_summary(
    standard: StandardRecord,
    chunks: list[ChunkRecord],
) -> StandardSummary:
    """기준서의 목적+적용범위+정의 청크를 결합하여 StandardSummary 생성."""
    # 목적 + 적용범위
    scope_chunks = [
        c for c in chunks
        if c.component == "main"
        and c.section_title in _SCOPE_TITLES
    ]
    if not scope_chunks:
        scope_chunks = [c for c in chunks if c.component == "main"][:5]

    scope_text = "\n".join(c.content_text for c in scope_chunks)
    scope_markdown = "\n\n".join(c.content_markdown for c in scope_chunks)

    # 정의 섹션
    def_chunks = [c for c in chunks if c.component == "definitions"]
    definitions_text = "\n".join(c.content_text for c in def_chunks)
    definitions_markdown = "\n\n".join(c.content_markdown for c in def_chunks)

    return StandardSummary(
        standard_id=standard.standard_id,
        title=standard.title,
        scope_text=scope_text,
        scope_markdown=scope_markdown,
        definitions_text=definitions_text,
        definitions_markdown=definitions_markdown,
    )
