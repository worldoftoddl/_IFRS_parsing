"""BC/IE 청크에서 본문 문단 참조를 추출한다.

두 가지 추출 전략:
1. section_heading: "### 계약의 식별(문단 9~16)" → 해당 섹션 아래 모든 청크가 문단 9~16에 링크
2. body_reference: 청크 본문 내 "문단 9~16" 패턴 → 개별 청크에 링크
"""

import re

from ingester.models import ChunkRecord, ParagraphLink

# ---------------------------------------------------------------------------
# 정규식
# ---------------------------------------------------------------------------

# 문단 범위: "문단 9~16", "문단 B34~B38", "문단 한82.1~한82.3"
_PARA_RANGE_RE = re.compile(
    r"문단\s*"
    r"(한?\s*\d+(?:\.\d+)*[A-Z]?|[A-Z]{1,3}\d+[A-Z]?(?:\.\d+)?)"
    r"\s*[~∼\-]\s*"
    r"(한?\s*\d+(?:\.\d+)*[A-Z]?|[A-Z]{1,3}\d+[A-Z]?(?:\.\d+)?)"
)

# 단일 문단: "문단 9", "문단 B34", "문단 AG5"
_PARA_SINGLE_RE = re.compile(
    r"문단\s*"
    r"(한?\s*\d+(?:\.\d+)*[A-Z]?|[A-Z]{1,3}\d+[A-Z]?(?:\.\d+)?)"
    r"(?![~∼\-\d])"  # 범위의 일부가 아닌 경우만
)

# 섹션 헤딩 내 괄호 참조: "### 제목(문단 X~Y)"
_HEADING_PARA_RE = re.compile(
    r"\(문단\s*"
    r"(한?\s*\d+(?:\.\d+)*[A-Z]?|[A-Z]{1,3}\d+[A-Z]?(?:\.\d+)?)"
    r"(?:\s*[~∼\-]\s*"
    r"(한?\s*\d+(?:\.\d+)*[A-Z]?|[A-Z]{1,3}\d+[A-Z]?(?:\.\d+)?))?"
    r"\)"
)


# ---------------------------------------------------------------------------
# 메인 API
# ---------------------------------------------------------------------------


def extract_links(
    standard_id: str,
    chunks: list[ChunkRecord],
) -> list[ParagraphLink]:
    """청크 리스트에서 BC/IE → 본문 참조 링크를 추출한다."""
    links: list[ParagraphLink] = []
    seen: set[tuple[str, str, str | None]] = set()  # (chunk_id, start, end)

    # 현재 섹션 헤딩의 참조 (해당 섹션 아래 모든 청크에 적용)
    heading_refs: list[tuple[str, str | None]] = []
    current_heading_component: str | None = None

    for chunk in chunks:
        # BC/IE가 아닌 청크는 건너뜀
        # IE 문단은 component가 'ag'로 분류되는 경우가 있으므로 para_number도 확인
        is_bc_ie = (
            chunk.component in ("bc", "ie")
            or (chunk.para_number and chunk.para_number.startswith(("BC", "IE")))
        )
        if not is_bc_ie:
            heading_refs = []
            current_heading_component = None
            continue

        effective_component = chunk.component
        if chunk.para_number and chunk.para_number.startswith("IE"):
            effective_component = "ie"
        elif chunk.para_number and chunk.para_number.startswith("BC"):
            effective_component = "bc"

        # 섹션 제목이 바뀌면 헤딩 참조 갱신
        if (chunk.section_title
                and effective_component != current_heading_component
                or (chunk.section_title and _has_heading_ref(chunk.section_title))):
            heading_refs = _extract_heading_refs(chunk.section_title)
            current_heading_component = effective_component

        # 1. 섹션 헤딩 기반 링크
        for start, end in heading_refs:
            key = (chunk.chunk_id, start, end)
            if key not in seen:
                seen.add(key)
                links.append(ParagraphLink(
                    standard_id=standard_id,
                    source_chunk_id=chunk.chunk_id,
                    source_component=effective_component,
                    source_para=chunk.para_number,
                    target_para_start=start,
                    target_para_end=end,
                    link_type="section_heading",
                ))

        # 2. 본문 내 참조 링크
        for start, end in _extract_body_refs(chunk.content_text):
            key = (chunk.chunk_id, start, end)
            if key not in seen:
                seen.add(key)
                links.append(ParagraphLink(
                    standard_id=standard_id,
                    source_chunk_id=chunk.chunk_id,
                    source_component=effective_component,
                    source_para=chunk.para_number,
                    target_para_start=start,
                    target_para_end=end,
                    link_type="body_reference",
                ))

    return links


# ---------------------------------------------------------------------------
# 내부 함수
# ---------------------------------------------------------------------------


def _has_heading_ref(title: str) -> bool:
    """섹션 제목에 문단 참조가 있는지 확인."""
    return bool(_HEADING_PARA_RE.search(title))


def _extract_heading_refs(title: str) -> list[tuple[str, str | None]]:
    """섹션 제목에서 문단 참조를 추출.

    Returns:
        [(start, end), ...] — end가 None이면 단일 문단
    """
    refs: list[tuple[str, str | None]] = []
    for m in _HEADING_PARA_RE.finditer(title):
        start = m.group(1).replace(" ", "")
        end = m.group(2).replace(" ", "") if m.group(2) else None
        refs.append((start, end))
    return refs


def _extract_body_refs(text: str) -> list[tuple[str, str | None]]:
    """본문 텍스트에서 문단 참조를 추출.

    Returns:
        [(start, end), ...] — end가 None이면 단일 문단
    """
    refs: list[tuple[str, str | None]] = []
    found_positions: set[int] = set()

    # 범위 참조 먼저 (단일 참조와 겹치지 않도록)
    for m in _PARA_RANGE_RE.finditer(text):
        start = m.group(1).replace(" ", "")
        end = m.group(2).replace(" ", "")
        refs.append((start, end))
        found_positions.add(m.start())

    # 단일 참조 (범위에 포함되지 않은 것만)
    for m in _PARA_SINGLE_RE.finditer(text):
        if m.start() not in found_positions:
            para = m.group(1).replace(" ", "")
            refs.append((para, None))

    return refs
