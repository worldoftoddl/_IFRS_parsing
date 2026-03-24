"""청크 후처리: 초과 청크 분할 + 정의 섹션 용어 분리.

regex 기반으로 처리하며, LLM은 사용하지 않는다.
"""

import re

from ingester.models import ChunkRecord

# 토큰 추정 임계값 (Upstage embedding-passage 최대 4000토큰)
_MAX_TOKENS = 3500  # 여유 두고 3500
_MAX_CHARS = _MAX_TOKENS * 2  # 한국어 ~2chars/token

# 정의 용어 패턴: *용어*: 정의 또는 *용어:* 정의 (bold/italic 조합)
_DEFINITION_TERM_RE = re.compile(
    r"^[\s\t]*\*{0,3}"           # 선행 공백 + bold/italic 마커
    r"([가-힣A-Za-z\s()（）]+?)"  # 용어명
    r"\*{0,3}"                    # bold/italic 닫기
    r"[\s:：]"                    # 콜론 구분
)

# 표 행 패턴
_TABLE_ROW_RE = re.compile(r"^\|.*\|$")


def split_oversized_chunks(
    chunks: list[ChunkRecord],
    max_chars: int = _MAX_CHARS,
) -> list[ChunkRecord]:
    """초과 청크를 분할하고 정의 용어를 분리한다."""
    result: list[ChunkRecord] = []

    for chunk in chunks:
        # 정의 섹션: 용어별 분리 시도
        if chunk.component == "definitions" and chunk.char_count > max_chars:
            split = _split_definition_chunk(chunk)
            if len(split) > 1:
                result.extend(split)
                continue

        # 일반 초과 청크: 표 또는 줄바꿈 기준 분할
        if chunk.char_count > max_chars:
            split = _split_by_structure(chunk, max_chars)
            result.extend(split)
        else:
            result.append(chunk)

    return result


def _split_definition_chunk(chunk: ChunkRecord) -> list[ChunkRecord]:
    """정의 청크를 용어별로 분리.

    패턴: 줄 시작이 *용어*: 또는 **용어**: 이면 새 정의 시작.
    """
    lines = chunk.content_markdown.split("\n")
    segments: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        # 빈 줄은 현재 세그먼트에 추가
        if not stripped:
            if current:
                current.append(line)
            continue

        # 새 용어 시작 감지: *용어*: 패턴 (줄 시작이 탭+italic/bold)
        is_new_term = (
            stripped.startswith("*") and ":" in stripped[:80]
            and not stripped.startswith("*이 ")  # 권위 선언 제외
            and not _TABLE_ROW_RE.match(stripped)
        )

        if is_new_term and current:
            segments.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        segments.append(current)

    # 세그먼트가 1개면 분리 실패 → 원본 반환
    if len(segments) <= 1:
        return [chunk]

    # 청크 생성
    result: list[ChunkRecord] = []
    for i, seg_lines in enumerate(segments):
        md = "\n".join(seg_lines).strip()
        if not md:
            continue
        plain = _strip_markdown(md)
        if not plain:
            continue

        suffix = f"-def{i}" if i > 0 else ""
        result.append(ChunkRecord(
            chunk_id=f"{chunk.chunk_id}{suffix}",
            standard_id=chunk.standard_id,
            para_number=chunk.para_number,
            component=chunk.component,
            section_title=chunk.section_title,
            authority=chunk.authority,
            content_text=plain,
            content_markdown=md,
            char_count=len(plain),
            token_estimate=max(1, len(plain) // 2),
        ))

    return result if result else [chunk]


def _split_by_structure(
    chunk: ChunkRecord, max_chars: int
) -> list[ChunkRecord]:
    """구조 기반 분할: 빈 줄, 표 경계, 또는 고정 크기로 분할."""
    lines = chunk.content_markdown.split("\n")

    # 빈 줄 기준으로 단락 그룹 만들기
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line.strip() and current:
            paragraphs.append("\n".join(current))
            current = []
        else:
            current.append(line)
    if current:
        paragraphs.append("\n".join(current))

    # 단락을 max_chars 이내로 그룹화
    groups: list[list[str]] = []
    current_group: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > max_chars and current_group:
            groups.append(current_group)
            current_group = [para]
            current_len = para_len
        else:
            current_group.append(para)
            current_len += para_len

    if current_group:
        groups.append(current_group)

    # 그룹이 1개면 분할 불가 → 강제 절단
    if len(groups) <= 1:
        return [_truncate_chunk(chunk, max_chars)]

    result: list[ChunkRecord] = []
    for i, group in enumerate(groups):
        md = "\n\n".join(group).strip()
        if not md:
            continue
        plain = _strip_markdown(md)
        if not plain:
            continue

        suffix = f"-pt{i+1}" if i > 0 else ""
        result.append(ChunkRecord(
            chunk_id=f"{chunk.chunk_id}{suffix}",
            standard_id=chunk.standard_id,
            para_number=chunk.para_number,
            component=chunk.component,
            section_title=chunk.section_title,
            authority=chunk.authority,
            content_text=plain,
            content_markdown=md,
            char_count=len(plain),
            token_estimate=max(1, len(plain) // 2),
        ))

    return result if result else [_truncate_chunk(chunk, max_chars)]


def _truncate_chunk(chunk: ChunkRecord, max_chars: int) -> ChunkRecord:
    """강제 절단 (최후 수단)."""
    plain = chunk.content_text[:max_chars]
    md = chunk.content_markdown[:max_chars]
    return ChunkRecord(
        chunk_id=chunk.chunk_id,
        standard_id=chunk.standard_id,
        para_number=chunk.para_number,
        component=chunk.component,
        section_title=chunk.section_title,
        authority=chunk.authority,
        content_text=plain,
        content_markdown=md,
        char_count=len(plain),
        token_estimate=max(1, len(plain) // 2),
    )


def _strip_markdown(text: str) -> str:
    """마크다운 서식 제거."""
    text = re.sub(r"<!--.*?-->", "", text)
    text = text.replace("***", "").replace("**", "").replace("*", "")
    text = re.sub(r"\[\^\d+\]", "", text)
    text = text.replace("\t", " ")
    text = re.sub(r"  +", " ", text)
    return text.strip()
