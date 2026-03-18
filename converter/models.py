"""K-IFRS IR(Intermediate Representation) 데이터 모델."""

from dataclasses import dataclass, field


@dataclass
class FormattedRun:
    """서식이 적용된 텍스트 조각."""

    text: str
    bold: bool = False
    italic: bool = False


@dataclass
class MetaInfo:
    """기준서 메타데이터 (파일명 기반 추출)."""

    standard_number: str   # "1016" or ""
    standard_title: str    # "유형자산" or "재무보고 개념체계"
    display_id: str        # "K-IFRS 1016" or "재무보고 개념체계"
    normalized_id: str     # "KIFRS1016" or "KIFRS_CF"


@dataclass
class SectionHeader:
    """섹션 헤더 (1x1 표에서 추출)."""

    text: str
    level: int             # 2 (major section) or 3 (sub-section)
    section_type: str      # "main", "ag", "bc", "ie", "definitions", "transition"


@dataclass
class AuthorityMarker:
    """권위 수준 선언 문구.

    '이 부록은 이 기준서의 일부를 구성한다' 등의 문구를 캡처한다.
    """

    text: str
    is_authoritative: bool  # True = 권위 있음, False = 비권위


@dataclass
class SubItem:
    """호/목 (⑴⑵⑶, ㈎㈏㈐ 등)."""

    marker: str
    content: str
    runs: list[FormattedRun] = field(default_factory=list)
    sub_sub_items: list["SubItem"] = field(default_factory=list)
    footnote_refs: list[int] = field(default_factory=list)


@dataclass
class NumberedParagraph:
    """번호 있는 문단 (원자 단위)."""

    para_number: str           # "1", "AG5", "BC12A", "한2.1"
    section_type: str
    content: str               # plain text
    runs: list[FormattedRun] = field(default_factory=list)
    sub_items: list[SubItem] = field(default_factory=list)
    is_fully_bold: bool = False
    is_korean_addition: bool = False
    footnote_refs: list[int] = field(default_factory=list)


@dataclass
class ContinuationText:
    """번호 없는 이어지는 텍스트."""

    content: str
    section_type: str
    runs: list[FormattedRun] = field(default_factory=list)
    is_fully_bold: bool = False
    footnote_refs: list[int] = field(default_factory=list)


@dataclass
class ContentTable:
    """내용 표 (다중 열/행)."""

    headers: list[str]
    rows: list[list[str]]
    section_type: str


@dataclass
class Footnote:
    """각주."""

    id: int
    content: str
    runs: list[FormattedRun] = field(default_factory=list)


IRElement = (
    MetaInfo | SectionHeader | AuthorityMarker
    | NumberedParagraph | ContinuationText | ContentTable
)
