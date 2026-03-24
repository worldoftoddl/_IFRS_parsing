"""기준서 식별용 요약 생성 (목적 + 적용범위 청크 결합)."""

from ingester.models import ChunkRecord, StandardRecord, StandardSummary

_SCOPE_TITLES = {"목적", "적용범위", "적용", "제1장 목적", "목적과 적용범위"}


def build_summary(
    standard: StandardRecord,
    chunks: list[ChunkRecord],
) -> StandardSummary:
    """기준서의 목적+적용범위 청크를 결합하여 StandardSummary 생성."""
    scope_chunks = [
        c for c in chunks
        if c.component == "main"
        and c.section_title in _SCOPE_TITLES
    ]

    # 일부 기준서는 섹션 제목 없이 바로 시작 → 첫 5개 main 청크를 폴백
    if not scope_chunks:
        scope_chunks = [c for c in chunks if c.component == "main"][:5]

    scope_text = "\n".join(c.content_text for c in scope_chunks)
    scope_markdown = "\n\n".join(c.content_markdown for c in scope_chunks)

    return StandardSummary(
        standard_id=standard.standard_id,
        title=standard.title,
        scope_text=scope_text,
        scope_markdown=scope_markdown,
    )
