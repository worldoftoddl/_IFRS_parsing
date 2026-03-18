"""K-IFRS DOCX → IR 파서.

기존 파서(Study/_database/pipeline/docx_parser.py)를 포크하여
서식 정보(bold/italic), 각주, authority_level 마커를 추가 추출한다.

Usage:
    from converter.docx_parser import parse_docx
    elements, footnotes, stats = parse_docx("IFRS_docx/.../xxx.docx")
"""

import io
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Optional

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table as DocxTable
from lxml import etree

from converter.models import (
    AuthorityMarker,
    ContentTable,
    ContinuationText,
    Footnote,
    FormattedRun,
    IRElement,
    MetaInfo,
    NumberedParagraph,
    SectionHeader,
    SubItem,
)

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

_NSMAP = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

# 섹션 감지 매핑 (우선순위: 구체적 → 일반적)
_SECTION_TEXT_MAP: list[tuple[str, str]] = [
    ("결론도출근거", "bc"),
    ("적용지침", "ag"),
    ("부록 B", "ag"),
    ("용어의 정의", "definitions"),
    ("부록 A", "definitions"),
    ("경과규정", "transition"),
    ("사례", "ie"),
    ("실무적용지침", "ie"),
    ("본 문", "main"),
    ("시행일", "main"),
]

# 문단번호 파싱 정규식
_PARA_NUMBER_RE = re.compile(
    r"^(한\s*\d+(?:\.\d+)*|\d+(?:\.\d+)*[A-Z]?|"
    r"AG\d+[A-Z]?(?:\.\d+)?|BC\d+[A-Z]?(?:\.\d+)?|BCE\.\d+[A-Z]?|"
    r"IE\d+[A-Z]?(?:\.\d+)?|B\d+(?:\.\d+)*[A-Z]?|C\d+[A-Z]?(?:\.\d+)?)$"
)

# 호/목 마커
_HO_MARKERS = set("⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿")
_MOK_MARKERS = set("㈎㈏㈐㈑㈒㈓㈔㈕㈖㈗")
_ALL_SUB_MARKERS = _HO_MARKERS | _MOK_MARKERS

# 저작권/영문 필터링
_COPYRIGHT_KEYWORDS = [
    "IFRS Foundation", "All rights reserved", "Copyright",
    "International Financial Reporting Standards",
    "Westferry Circus", "permitted to reproduce",
    "COPYRIGHT NOTICE",
    "모든 저작권은 보호됩니다",
    "www.ifrs.org",
]

# 비표준 파일 ID 매핑
_ETC_ID_MAP = {
    "경영진설명서_작성을_위한_개념체계_번역서": ("경영진설명서 개념체계", "KIFRS_CF_MgtCommentary"),
    "국제회계기준_실무서_2_중요성에_대한_판단_번역서": ("실무서 2 중요성", "KIFRS_PS2_Materiality"),
    "시행중_K-IFRS_재무보고를_위한_개념체계": ("재무보고 개념체계", "KIFRS_CF"),
}

# 권위 수준 감지 패턴
_AUTHORITY_POSITIVE_RE = re.compile(
    r"(이\s*부록은.*일부를\s*구성한다|동등한\s*권위)"
)
_AUTHORITY_NEGATIVE_RE = re.compile(
    r"일부를\s*구성하는\s*것은\s*아니다"
)

# XML 1.0 유효하지 않은 문자
_INVALID_XML_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f"
    "\ud800-\udfff\ufdd0-\ufddf\ufffe\uffff]"
)


# ---------------------------------------------------------------------------
# DOCX 열기 (백슬래시 경로 수정 + XML 정제)
# ---------------------------------------------------------------------------


def _open_docx(docx_path: str) -> tuple[Document, dict[str, bytes]]:
    """DOCX 파일을 열고, 정제된 Document와 원본 파트 데이터를 반환한다.

    Returns:
        (Document, raw_parts): raw_parts는 정제 후 파트 이름→바이트 매핑
    """
    buf = io.BytesIO()
    raw_parts: dict[str, bytes] = {}

    with zipfile.ZipFile(docx_path, "r") as zin:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                fixed_name = item.filename.replace("\\", "/")
                if fixed_name.endswith(".xml") or fixed_name.endswith(".rels"):
                    text = data.decode("utf-8", errors="replace")
                    text = _INVALID_XML_RE.sub("", text)
                    data = text.encode("utf-8")
                raw_parts[fixed_name] = data
                item.filename = fixed_name
                zout.writestr(item, data)

    buf.seek(0)
    return Document(buf), raw_parts


# ---------------------------------------------------------------------------
# XML 유틸리티
# ---------------------------------------------------------------------------


def _xml_para_text(p_elem) -> str:
    """<w:p>에서 전체 텍스트 추출 (탭/줄바꿈 포함)."""
    parts: list[str] = []
    for r_elem in p_elem.findall(qn("w:r")):
        for child in r_elem:
            if child.tag == qn("w:t"):
                parts.append(child.text or "")
            elif child.tag == qn("w:tab"):
                parts.append("\t")
            elif child.tag in (qn("w:br"), qn("w:cr")):
                parts.append("\n")
    return "".join(parts)


def _xml_para_runs(p_elem) -> list[FormattedRun]:
    """<w:p>에서 서식 정보 포함 run 리스트 추출."""
    runs: list[FormattedRun] = []

    # 문단 수준 기본 서식 확인 (pPr/rPr에서 상속)
    p_bold = False
    p_italic = False
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is not None:
        prPr = pPr.find(qn("w:rPr"))
        if prPr is not None:
            p_bold = _check_bold(prPr)
            p_italic = _check_italic(prPr)

    for r_elem in p_elem.findall(qn("w:r")):
        text_parts: list[str] = []
        for child in r_elem:
            if child.tag == qn("w:t"):
                text_parts.append(child.text or "")
            elif child.tag == qn("w:tab"):
                text_parts.append("\t")
            elif child.tag in (qn("w:br"), qn("w:cr")):
                text_parts.append("\n")

        text = "".join(text_parts)
        if not text:
            continue

        # run 수준 서식
        rPr = r_elem.find(qn("w:rPr"))
        if rPr is not None:
            bold = _check_bold(rPr)
            italic = _check_italic(rPr)
        else:
            bold = p_bold
            italic = p_italic

        runs.append(FormattedRun(text=text, bold=bold, italic=italic))

    return runs


def _check_bold(rPr) -> bool:
    """rPr 요소에서 bold 여부 확인."""
    b = rPr.find(qn("w:b"))
    if b is not None:
        val = b.get(qn("w:val"))
        return val is None or val not in ("0", "false")
    bCs = rPr.find(qn("w:bCs"))
    if bCs is not None:
        val = bCs.get(qn("w:val"))
        return val is None or val not in ("0", "false")
    return False


def _check_italic(rPr) -> bool:
    """rPr 요소에서 italic 여부 확인."""
    i = rPr.find(qn("w:i"))
    if i is not None:
        val = i.get(qn("w:val"))
        return val is None or val not in ("0", "false")
    iCs = rPr.find(qn("w:iCs"))
    if iCs is not None:
        val = iCs.get(qn("w:val"))
        return val is None or val not in ("0", "false")
    return False


def _is_fully_bold(runs: list[FormattedRun]) -> bool:
    """모든 non-whitespace run이 bold인지 확인."""
    content_runs = [r for r in runs if r.text.strip()]
    if not content_runs:
        return False
    return all(r.bold for r in content_runs)


def _extract_footnote_refs(p_elem) -> list[int]:
    """<w:p>에서 각주 참조 ID 추출."""
    refs: list[int] = []
    for fn_ref in p_elem.iter(qn("w:footnoteReference")):
        fid = fn_ref.get(qn("w:id"))
        if fid and fid.isdigit() and int(fid) > 0:
            refs.append(int(fid))
    return refs


def _xml_para_style(p_elem) -> Optional[str]:
    """<w:p>에서 스타일 ID 추출."""
    pPr = p_elem.find(qn("w:pPr"))
    if pPr is not None:
        pStyle = pPr.find(qn("w:pStyle"))
        if pStyle is not None:
            return pStyle.get(qn("w:val"))
    return None


def _get_unique_cells(row):
    """행에서 중복 셀(병합) 제거."""
    seen: set[int] = set()
    cells = []
    for cell in row.cells:
        tc_id = id(cell._tc)
        if tc_id not in seen:
            seen.add(tc_id)
            cells.append(cell)
    return cells


# ---------------------------------------------------------------------------
# 각주 파싱
# ---------------------------------------------------------------------------


def _parse_footnotes(raw_parts: dict[str, bytes]) -> dict[int, Footnote]:
    """word/footnotes.xml에서 각주를 파싱한다."""
    footnotes: dict[int, Footnote] = {}

    fn_data = raw_parts.get("word/footnotes.xml")
    if fn_data is None:
        return footnotes

    root = etree.fromstring(fn_data)
    for fn_elem in root.findall("w:footnote", _NSMAP):
        fid_str = fn_elem.get(qn("w:id"))
        if not fid_str or not fid_str.lstrip("-").isdigit():
            continue
        fid = int(fid_str)
        if fid <= 0:  # 0과 -1은 separator/continuation separator
            continue

        # 각주 내 모든 문단 텍스트 수집
        texts: list[str] = []
        all_runs: list[FormattedRun] = []
        for p_elem in fn_elem.findall("w:p", _NSMAP):
            p_text = _xml_para_text(p_elem)
            if p_text.strip():
                texts.append(p_text.strip())
            p_runs = _xml_para_runs(p_elem)
            all_runs.extend(p_runs)

        content = " ".join(texts)
        if content:
            footnotes[fid] = Footnote(id=fid, content=content, runs=all_runs)

    return footnotes


# ---------------------------------------------------------------------------
# 메타데이터 유틸리티
# ---------------------------------------------------------------------------


def _extract_title_from_filename(filename: str) -> str:
    """파일명에서 기준서 제목 부분 추출."""
    m = re.search(r"제\d+호[_\s]*([^(]+)", filename)
    if m:
        return m.group(1).strip().rstrip("_")
    return ""


def _make_meta_from_filename(filename: str) -> MetaInfo:
    """파일명에서 MetaInfo 생성."""
    stem = Path(filename).stem

    # 표준 기준서 (제XXXX호)
    m = re.search(r"제(\d+)호", filename)
    if m:
        number = m.group(1)
        title = _extract_title_from_filename(filename)
        return MetaInfo(
            standard_number=number,
            standard_title=title,
            display_id=f"K-IFRS {number}",
            normalized_id=f"KIFRS{number}",
        )

    # 비표준 파일
    for key, (display, normalized) in _ETC_ID_MAP.items():
        if key in stem:
            return MetaInfo(
                standard_number="",
                standard_title=display,
                display_id=display,
                normalized_id=normalized,
            )

    # 폴백
    return MetaInfo(
        standard_number="",
        standard_title=stem[:40],
        display_id=stem[:40],
        normalized_id=re.sub(r"[^\w]", "_", stem[:40]),
    )


# ---------------------------------------------------------------------------
# 분류 로직
# ---------------------------------------------------------------------------


def _detect_section_from_text(text: str) -> Optional[str]:
    """1x1 표 텍스트에서 섹션 타입 감지."""
    text_clean = text.strip()
    for keyword, section_type in _SECTION_TEXT_MAP:
        if keyword in text_clean:
            return section_type
    if "부록" in text_clean:
        return "ag"
    return None


def _is_copyright(text: str) -> bool:
    return any(kw in text for kw in _COPYRIGHT_KEYWORDS)


def _is_revision_table(all_text: str, n_rows: int) -> bool:
    """개정이력 표 감지."""
    revision_kw = ["수정목록", "개정 및 수정", "제⋅개정", "제·개정", "제/개정"]
    if any(kw in all_text for kw in revision_kw):
        return True
    hit = sum(1 for kw in ["개정", "제정", "공표", "시행일"] if kw in all_text)
    return hit >= 2 and n_rows >= 3


def _is_meta_or_toc_table(all_text: str, seen_section: bool) -> bool:
    """메타/표지/목차 표 감지."""
    if seen_section:
        return False
    if "목차" in all_text or "목 차" in all_text:
        return True
    meta_kw = ["기업회계기준서", "한국채택국제회계기준", "기업회계기준해석서"]
    hit = sum(1 for kw in meta_kw if kw in all_text)
    return hit >= 1 and len(all_text) < 500


def _check_authority_marker(text: str) -> Optional[AuthorityMarker]:
    """권위 수준 선언 문구를 감지한다."""
    if _AUTHORITY_NEGATIVE_RE.search(text):
        return AuthorityMarker(text=text.strip(), is_authoritative=False)
    if _AUTHORITY_POSITIVE_RE.search(text):
        return AuthorityMarker(text=text.strip(), is_authoritative=True)
    return None


def _classify_paragraph(
    raw_text: str,
    current_section_type: str,
    runs: list[FormattedRun],
    footnote_refs: list[int],
):
    """문단 텍스트를 IR 요소로 분류.

    Returns:
        NumberedParagraph | SubItem | ContinuationText | AuthorityMarker | None
    """
    if not raw_text or not raw_text.strip():
        return None

    if _is_copyright(raw_text):
        return None

    stripped = raw_text.strip()

    # 권위 수준 마커 감지 (짧은 선언 문구만)
    if len(stripped) < 200:
        marker = _check_authority_marker(stripped)
        if marker is not None:
            return marker

    fully_bold = _is_fully_bold(runs)

    # --- Tab 기반 분류 ---
    if "\t" in raw_text:
        first_tab = raw_text.index("\t")
        before_tab = raw_text[:first_tab].strip()
        after_tab = raw_text[first_tab + 1:]

        if before_tab:
            # 번호 + TAB + 내용
            if _PARA_NUMBER_RE.match(before_tab):
                pnum = before_tab.replace(" ", "")
                # "한" 접두어 → content run에서 번호 부분 제외
                content_runs = _strip_number_from_runs(runs, before_tab)
                return NumberedParagraph(
                    para_number=pnum,
                    section_type=current_section_type,
                    content=after_tab.strip(),
                    runs=content_runs,
                    is_fully_bold=fully_bold,
                    is_korean_addition=pnum.startswith("한"),
                    footnote_refs=footnote_refs,
                )
            # 마커 + TAB + 내용
            if len(before_tab) == 1 and before_tab in _ALL_SUB_MARKERS:
                content_runs = _strip_number_from_runs(runs, before_tab)
                return SubItem(
                    marker=before_tab,
                    content=after_tab.strip(),
                    runs=content_runs,
                    footnote_refs=footnote_refs,
                )
        else:
            # 선행 TAB → 호/목 후보
            inner = after_tab.lstrip("\t ")
            if inner and inner[0] in _ALL_SUB_MARKERS:
                marker = inner[0]
                rest = inner[1:].lstrip("\t ").strip()
                return SubItem(
                    marker=marker,
                    content=rest,
                    runs=runs,
                    footnote_refs=footnote_refs,
                )

    # --- Fallback: 공백 기준 문단번호 ---
    parts = stripped.split(None, 1)
    if len(parts) == 2 and _PARA_NUMBER_RE.match(parts[0]):
        pnum = parts[0].replace(" ", "")
        content_runs = _strip_number_from_runs(runs, parts[0])
        return NumberedParagraph(
            para_number=pnum,
            section_type=current_section_type,
            content=parts[1],
            runs=content_runs,
            is_fully_bold=fully_bold,
            is_korean_addition=pnum.startswith("한"),
            footnote_refs=footnote_refs,
        )

    # --- 마커로 시작 (탭 없는 경우) ---
    if stripped and stripped[0] in _ALL_SUB_MARKERS:
        marker = stripped[0]
        rest = stripped[1:].lstrip("\t ").strip()
        return SubItem(
            marker=marker,
            content=rest,
            runs=runs,
            footnote_refs=footnote_refs,
        )

    # --- ContinuationText ---
    return ContinuationText(
        content=stripped,
        section_type=current_section_type,
        runs=runs,
        is_fully_bold=fully_bold,
        footnote_refs=footnote_refs,
    )


def _strip_number_from_runs(
    runs: list[FormattedRun], number_text: str
) -> list[FormattedRun]:
    """run 리스트에서 문단 번호 부분과 탭을 제거하여 content run만 반환."""
    if not runs:
        return runs

    result: list[FormattedRun] = []
    remaining = number_text
    past_number = False

    for run in runs:
        if past_number:
            result.append(run)
            continue

        text = run.text
        # 번호 부분과 탭을 건너뛴다
        if remaining:
            # remaining이 이 run 안에 있는지 확인
            stripped = text.lstrip()
            if stripped.startswith(remaining) or remaining.startswith(stripped.rstrip()):
                # 번호가 이 run에 있음
                if len(stripped) > len(remaining):
                    leftover = stripped[len(remaining):].lstrip("\t ")
                    if leftover:
                        result.append(FormattedRun(
                            text=leftover, bold=run.bold, italic=run.italic
                        ))
                    past_number = True
                else:
                    remaining = remaining[len(stripped.rstrip()):]
                continue

        # 탭만 있는 run은 건너뛴다
        if text.strip() == "" and ("\t" in text or text == " "):
            if not past_number:
                past_number = True  # 탭 이후는 content
            continue

        past_number = True
        result.append(run)

    return result if result else runs


def _classify_table(
    table: DocxTable,
    current_section_type: str,
    stats: dict,
    seen_section: bool,
):
    """표를 IR 요소로 분류.

    Returns:
        SectionHeader | ContentTable | None
    """
    rows = list(table.rows)
    if not rows:
        return None

    first_cells = _get_unique_cells(rows[0])
    n_rows = len(rows)
    n_cols = len(first_cells)

    # --- 1행 1열: 섹션 헤더 후보 ---
    if n_rows == 1 and n_cols == 1:
        text = first_cells[0].text.strip()
        if not text:
            return None

        if len(text) > 100:
            stats["skipped_long_1x1"] = stats.get("skipped_long_1x1", 0) + 1
            return None

        section_type = _detect_section_from_text(text)
        if section_type is not None and len(text) < 50:
            return SectionHeader(text=text, level=2, section_type=section_type)

        if len(text) < 30:
            return SectionHeader(
                text=text, level=3, section_type=current_section_type
            )

        stats["skipped_medium_1x1"] = stats.get("skipped_medium_1x1", 0) + 1
        return None

    # --- 다중 행/열 ---
    all_text = " ".join(c.text for r in rows for c in r.cells)

    if _is_revision_table(all_text, n_rows):
        stats["revision_tables"] = stats.get("revision_tables", 0) + 1
        return None

    if _is_meta_or_toc_table(all_text, seen_section):
        stats["meta_tables"] = stats.get("meta_tables", 0) + 1
        return None

    if _is_copyright(all_text):
        stats["copyright_tables"] = stats.get("copyright_tables", 0) + 1
        return None

    # --- 내용 표 ---
    headers = [c.text.strip().replace("\n", " ") for c in first_cells]
    data_rows = []
    for row in rows[1:]:
        cells = _get_unique_cells(row)
        data_rows.append([c.text.strip().replace("\n", " ") for c in cells])

    return ContentTable(
        headers=headers, rows=data_rows, section_type=current_section_type
    )


# ---------------------------------------------------------------------------
# 메인 API
# ---------------------------------------------------------------------------


def parse_docx(
    docx_path: str,
) -> tuple[list[IRElement], dict[int, Footnote], dict]:
    """DOCX 파일을 파싱하여 (IR 요소 리스트, 각주 dict, 통계 dict) 반환."""
    doc, raw_parts = _open_docx(docx_path)
    path = Path(docx_path)
    meta = _make_meta_from_filename(path.name)

    # 각주 파싱
    footnotes = _parse_footnotes(raw_parts)

    elements: list[IRElement] = [meta]
    current_section = "main"
    last_numbered: Optional[NumberedParagraph] = None
    seen_section = False

    stats: dict = defaultdict(int)
    style_dist: dict = defaultdict(int)

    body = doc.element.body
    for child in body:
        tag = child.tag

        # ---- Paragraph ----
        if tag == qn("w:p"):
            raw = _xml_para_text(child)
            style_id = _xml_para_style(child)

            style_dist[style_id or "(none)"] += 1
            stats["total_paragraphs"] += 1

            if not raw or not raw.strip():
                stats["empty_paragraphs"] += 1
                continue

            runs = _xml_para_runs(child)
            fn_refs = _extract_footnote_refs(child)

            el = _classify_paragraph(raw, current_section, runs, fn_refs)
            if el is None:
                stats["filtered_paragraphs"] += 1
                continue

            if isinstance(el, AuthorityMarker):
                elements.append(el)
                stats["authority_markers"] += 1
                continue

            if isinstance(el, SubItem):
                if last_numbered is not None:
                    if el.marker in _MOK_MARKERS:
                        if last_numbered.sub_items:
                            last_numbered.sub_items[-1].sub_sub_items.append(el)
                        else:
                            last_numbered.sub_items.append(el)
                    else:
                        last_numbered.sub_items.append(el)
                    stats["sub_items"] += 1
                else:
                    elements.append(ContinuationText(
                        content=f"{el.marker} {el.content}",
                        section_type=current_section,
                        runs=el.runs,
                        footnote_refs=el.footnote_refs,
                    ))
                    stats["orphan_sub_items"] += 1
                continue

            if isinstance(el, NumberedParagraph):
                el.section_type = current_section
                elements.append(el)
                last_numbered = el
                stats["numbered_paragraphs"] += 1

            elif isinstance(el, ContinuationText):
                el.section_type = current_section
                elements.append(el)
                stats["continuation_texts"] += 1

        # ---- Table ----
        elif tag == qn("w:tbl"):
            stats["total_tables"] += 1
            tbl = DocxTable(child, body)
            el = _classify_table(tbl, current_section, stats, seen_section)

            if el is None:
                continue

            if isinstance(el, SectionHeader):
                current_section = el.section_type
                elements.append(el)
                last_numbered = None
                seen_section = True
                stats["section_headers"] += 1

            elif isinstance(el, ContentTable):
                el.section_type = current_section
                elements.append(el)
                stats["content_tables"] += 1

        # ---- Structured Document Tag (SDT) ----
        elif tag == qn("w:sdt"):
            sdt_content = child.find(qn("w:sdtContent"))
            if sdt_content is None:
                continue
            for sub in sdt_content:
                if sub.tag == qn("w:p"):
                    raw = _xml_para_text(sub)
                    if not raw or not raw.strip():
                        continue
                    runs = _xml_para_runs(sub)
                    fn_refs = _extract_footnote_refs(sub)
                    el = _classify_paragraph(raw, current_section, runs, fn_refs)
                    if isinstance(el, NumberedParagraph):
                        el.section_type = current_section
                        elements.append(el)
                        last_numbered = el
                        stats["numbered_paragraphs"] += 1
                    elif isinstance(el, ContinuationText):
                        el.section_type = current_section
                        elements.append(el)
                        stats["continuation_texts"] += 1
                    elif isinstance(el, SubItem) and last_numbered:
                        if el.marker in _MOK_MARKERS and last_numbered.sub_items:
                            last_numbered.sub_items[-1].sub_sub_items.append(el)
                        else:
                            last_numbered.sub_items.append(el)
                        stats["sub_items"] += 1
                    elif isinstance(el, AuthorityMarker):
                        elements.append(el)
                        stats["authority_markers"] += 1

    stats["style_distribution"] = dict(style_dist)
    stats["footnote_count"] = len(footnotes)
    return elements, footnotes, dict(stats)
