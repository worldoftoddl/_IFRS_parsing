"""구조 보존 마크다운 → 청크 파서.

Stage 1이 생성한 마크다운 파일을 파싱하여
StandardRecord, ChunkRecord, FootnoteRecord 리스트를 생성한다.
"""

import re
from pathlib import Path

from ingester.models import ChunkRecord, FootnoteRecord, StandardRecord

# ---------------------------------------------------------------------------
# 정규식
# ---------------------------------------------------------------------------

# 번호 문단 시작 패턴 (TAB 구분)
_PARA_LINE_RE = re.compile(
    r"^(\*\*)?"                           # optional bold open
    r"(한\s*\d+(?:\.\d+)*"               # 한국 추가
    r"|\d+(?:\.\d+)*[A-Z]?"              # 일반 번호
    r"|AG\d+[A-Z]?(?:\.\d+)?"            # 적용지침
    r"|BC\d+[A-Z]?(?:\.\d+)?"            # 결론도출근거
    r"|BCE?\.\d+[A-Z]?"                  # BC 부록
    r"|IE\d+[A-Z]?(?:\.\d+)?"            # 적용사례
    r"|B\d+(?:\.\d+)*[A-Z]?"             # 부록B
    r"|C\d+[A-Z]?(?:\.\d+)?"             # 경과규정
    r"|SP\d+\.\d+"                        # 개념체계
    r")"
    r"\s*\t",                             # TAB 구분자
    re.MULTILINE,
)

# 메타데이터 코멘트
_PARA_COMMENT_RE = re.compile(r"^<!--\s*para:\s*(\S+)(.*?)-->$")
_COMPONENT_COMMENT_RE = re.compile(
    r"^<!--\s*component:\s*(\S+)\s*\|\s*authority:\s*(\d+)\s*-->$"
)
_AUTHORITY_DECL_RE = re.compile(r"^<!--\s*authority_declaration:")

# 호/목 마커
_SUBITEM_RE = re.compile(r"^\t+[⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿㈎㈏㈐㈑㈒㈓㈔㈕㈖㈗]")

# 표
_TABLE_ROW_RE = re.compile(r"^\|.*\|$")
_TABLE_SEP_RE = re.compile(r"^\|[\s\-|]+\|$")

# 각주 정의
_FOOTNOTE_DEF_RE = re.compile(r"^\[\^(\d+)\]:\s*(.+)$")

# 프론트매터
_FRONTMATTER_KV_RE = re.compile(r'^(\w+):\s*(.+)$')


# ---------------------------------------------------------------------------
# 프론트매터 파싱
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """YAML 프론트매터를 파싱하여 (dict, end_pos) 반환."""
    if not text.startswith("---"):
        return {}, 0

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, 0

    block = text[4:end]
    data: dict[str, str] = {}
    for line in block.split("\n"):
        m = _FRONTMATTER_KV_RE.match(line)
        if m:
            key = m.group(1)
            val = m.group(2).strip().strip('"')
            data[key] = val

    return data, end + 5  # skip past closing ---\n


def _make_standard_record(fm: dict[str, str], source_file: str) -> StandardRecord:
    """프론트매터 dict에서 StandardRecord 생성."""
    components_raw = fm.get("components", "")
    # "[main, ag, bc]" → ["main", "ag", "bc"]
    components = [
        c.strip() for c in components_raw.strip("[]").split(",") if c.strip()
    ]

    return StandardRecord(
        standard_id=fm.get("standard_id", ""),
        standard_number=fm.get("standard_number"),
        title=fm.get("title", ""),
        standard_type=fm.get("standard_type", ""),
        standard_family=fm.get("standard_family", ""),
        original_number=fm.get("original_number"),
        base_authority=int(fm.get("base_authority", "1")),
        last_amended_year=fm.get("last_amended_year"),
        components=components,
        has_korean_additions=fm.get("has_korean_additions", "false") == "true",
        korean_paragraph_count=int(fm.get("korean_paragraph_count", "0")),
        source_file=source_file,
    )


# ---------------------------------------------------------------------------
# 마크다운 서식 제거 (plain text 변환)
# ---------------------------------------------------------------------------


def _strip_markdown(text: str) -> str:
    """마크다운 서식을 제거하여 임베딩용 plain text로 변환."""
    # HTML 코멘트 제거
    text = re.sub(r"<!--.*?-->", "", text)
    # bold/italic 마커 제거
    text = text.replace("***", "").replace("**", "").replace("*", "")
    # 각주 참조 제거
    text = re.sub(r"\[\^\d+\]", "", text)
    # 탭을 공백으로
    text = text.replace("\t", " ")
    # 연속 공백 정리
    text = re.sub(r"  +", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# 청크 ID 생성
# ---------------------------------------------------------------------------


def _make_chunk_id(normalized_id: str, component: str, para_number: str | None) -> str:
    """청크 ID 생성: KIFRS1115-main-9"""
    if para_number:
        return f"{normalized_id}-{component}-{para_number}"
    return f"{normalized_id}-{component}-nonum"


def _normalize_id(standard_id: str) -> str:
    """standard_id를 정규화: 'K-IFRS 1115' → 'KIFRS1115'"""
    return re.sub(r"[^A-Za-z0-9가-힣]", "", standard_id)


# ---------------------------------------------------------------------------
# 메인 파서
# ---------------------------------------------------------------------------


def parse_markdown_file(
    file_path: str | Path,
) -> tuple[StandardRecord, list[ChunkRecord], list[FootnoteRecord]]:
    """마크다운 파일을 파싱하여 (StandardRecord, chunks, footnotes) 반환."""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")

    # 프론트매터
    fm, body_start = _parse_frontmatter(text)
    source_rel = str(path.relative_to(path.parent.parent.parent))
    standard = _make_standard_record(fm, source_rel)
    normalized_id = _normalize_id(standard.standard_id)

    body = text[body_start:]
    lines = body.split("\n")

    # 상태
    current_component = "main"
    current_authority = standard.base_authority
    current_section_title: str | None = None

    # 청크 수집
    chunks: list[ChunkRecord] = []
    footnotes: list[FootnoteRecord] = []

    # 현재 청크 축적
    current_para: str | None = None
    current_chunk_lines: list[str] = []
    chunk_component = "main"
    chunk_authority = 1
    chunk_section_title: str | None = None

    def _flush_chunk():
        """축적된 줄로부터 ChunkRecord를 생성하고 리스트에 추가."""
        nonlocal current_para, current_chunk_lines

        if not current_chunk_lines:
            return

        md_content = "\n".join(current_chunk_lines).strip()
        if not md_content:
            current_chunk_lines = []
            return

        plain_text = _strip_markdown(md_content)
        if not plain_text:
            current_chunk_lines = []
            return

        chunk_id = _make_chunk_id(normalized_id, chunk_component, current_para)
        # 중복 chunk_id 방지
        existing_ids = {c.chunk_id for c in chunks}
        if chunk_id in existing_ids:
            suffix = 1
            while f"{chunk_id}-{suffix}" in existing_ids:
                suffix += 1
            chunk_id = f"{chunk_id}-{suffix}"

        char_count = len(plain_text)
        chunks.append(ChunkRecord(
            chunk_id=chunk_id,
            standard_id=standard.standard_id,
            para_number=current_para,
            component=chunk_component,
            section_title=chunk_section_title,
            authority=chunk_authority,
            content_text=plain_text,
            content_markdown=md_content,
            char_count=char_count,
            token_estimate=max(1, char_count // 2),  # 한국어 ~2chars/token
        ))

        # 리셋
        current_para = None
        current_chunk_lines = []

    for line in lines:
        stripped = line.strip()

        # --- 각주 정의 (파일 하단) ---
        fn_match = _FOOTNOTE_DEF_RE.match(stripped)
        if fn_match:
            _flush_chunk()
            footnotes.append(FootnoteRecord(
                standard_id=standard.standard_id,
                footnote_number=int(fn_match.group(1)),
                content=fn_match.group(2),
            ))
            continue

        # --- 섹션 헤더 (## level 2) ---
        if stripped.startswith("## ") and not stripped.startswith("### "):
            _flush_chunk()
            # 다음 줄이 <!-- component --> 코멘트일 수 있으므로 여기선 제목만 저장
            current_section_title = stripped[3:].strip()
            continue

        # --- 서브섹션 헤더 (### level 3) ---
        if stripped.startswith("### "):
            _flush_chunk()
            current_section_title = stripped[4:].strip()
            # IAS 계열: "용어의 정의" 이후 서브섹션이 나오면 본문 복귀
            # 정의 섹션 자체는 ### 없이 연속 텍스트로 구성됨
            if current_component == "definitions":
                current_component = "main"
                current_authority = standard.base_authority
            continue

        # --- H1 (# 기준서 제목) → 건너뜀 ---
        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue

        # --- 컴포넌트 메타데이터 코멘트 ---
        comp_match = _COMPONENT_COMMENT_RE.match(stripped)
        if comp_match:
            current_component = comp_match.group(1)
            current_authority = int(comp_match.group(2))
            continue

        # --- 권위 선언 코멘트 → 건너뜀 ---
        if _AUTHORITY_DECL_RE.match(stripped):
            continue

        # --- 문단 메타데이터 코멘트 ---
        para_match = _PARA_COMMENT_RE.match(stripped)
        if para_match:
            continue

        # --- 수평선 (---) → 건너뜀 ---
        if stripped == "---":
            continue

        # --- 빈 줄 ---
        if not stripped:
            continue

        # --- 권위 선언 텍스트 (italic) ---
        if stripped.startswith("*") and ("구성하는 것은 아니다" in stripped
                                         or "일부를 구성한다" in stripped
                                         or "동등한 권위" in stripped):
            # 권위 선언은 별도 청크로 만들지 않음 (이미 component 메타에 반영)
            continue

        # --- 번호 문단 시작 감지 ---
        para_line_match = _PARA_LINE_RE.match(line)
        if para_line_match:
            # 이전 청크 플러시
            _flush_chunk()

            # 새 청크 시작
            current_para = para_line_match.group(2).replace(" ", "")
            chunk_component = current_component
            chunk_authority = current_authority
            chunk_section_title = current_section_title
            current_chunk_lines.append(line)
            continue

        # --- 호/목 (⑴⑵⑶, ㈎㈏㈐) ---
        if _SUBITEM_RE.match(line):
            current_chunk_lines.append(line)
            continue

        # --- 표 ---
        if _TABLE_ROW_RE.match(stripped) or _TABLE_SEP_RE.match(stripped):
            current_chunk_lines.append(line)
            continue

        # --- ContinuationText / 기타 텍스트 ---
        if current_chunk_lines:
            # 현재 청크에 어태치
            current_chunk_lines.append(line)
        else:
            # 독립 텍스트 (번호 없음) → 독립 청크
            _flush_chunk()
            current_para = None
            chunk_component = current_component
            chunk_authority = current_authority
            chunk_section_title = current_section_title
            current_chunk_lines.append(line)

    # 마지막 청크 플러시
    _flush_chunk()

    # 통계 업데이트
    standard.total_chunks = len(chunks)
    return standard, chunks, footnotes
