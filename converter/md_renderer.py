"""IR → 구조 보존 마크다운 렌더러.

사람이 검수할 수 있으면서 2단계에서 기계적으로 파싱 가능한 마크다운을 생성한다.

메타데이터 인코딩 방식:
    - YAML 프론트매터: 기준서 메타데이터
    - HTML 코멘트 (<!-- -->): 기계 파싱용 메타데이터
    - 마크다운 서식: **bold**(핵심 원칙), *italic*(정의 용어)
    - 각주: [^N] 문법, 파일 하단에 모음
"""

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
)

# ---------------------------------------------------------------------------
# 섹션 타입 → authority_level 매핑
# ---------------------------------------------------------------------------

_SECTION_AUTHORITY: dict[str, int] = {
    "main": 1,
    "definitions": 1,
    "ag": 1,
    "transition": 1,
    "ie": 4,
    "bc": 4,
}

# ---------------------------------------------------------------------------
# run → 서식 마크다운 변환
# ---------------------------------------------------------------------------


def _runs_to_markdown(runs: list[FormattedRun], is_fully_bold: bool) -> str:
    """FormattedRun 리스트를 마크다운 서식 텍스트로 변환."""
    if not runs:
        return ""

    # 인접한 동일 서식 run을 병합
    merged: list[FormattedRun] = []
    for run in runs:
        if not run.text:
            continue
        if merged and merged[-1].bold == run.bold and merged[-1].italic == run.italic:
            merged[-1] = FormattedRun(
                text=merged[-1].text + run.text,
                bold=run.bold,
                italic=run.italic,
            )
        else:
            merged.append(FormattedRun(text=run.text, bold=run.bold, italic=run.italic))

    parts: list[str] = []
    for run in merged:
        text = run.text
        if not text:
            continue

        # 공백/탭만 있는 run은 그대로
        if not text.strip():
            parts.append(text)
            continue

        if is_fully_bold:
            # 전체 bold 문단이므로 italic만 표시
            if run.italic:
                parts.append(f"*{text}*")
            else:
                parts.append(text)
        else:
            if run.bold and run.italic:
                parts.append(f"***{text}***")
            elif run.bold:
                parts.append(f"**{text}**")
            elif run.italic:
                parts.append(f"*{text}*")
            else:
                parts.append(text)

    return "".join(parts)


# ---------------------------------------------------------------------------
# 각주 참조 삽입
# ---------------------------------------------------------------------------


def _append_footnote_refs(text: str, refs: list[int]) -> str:
    """텍스트 끝에 각주 참조 마커를 추가한다."""
    if not refs:
        return text
    markers = "".join(f"[^{r}]" for r in refs)
    return text.rstrip() + markers


# ---------------------------------------------------------------------------
# 메인 렌더러
# ---------------------------------------------------------------------------


def _collect_render_stats(
    elements: list[IRElement],
) -> tuple[list[str], bool, int]:
    """요소 리스트에서 렌더링 통계를 수집한다.

    Returns:
        (components_present, has_korean_additions, korean_paragraph_count)
    """
    components: set[str] = set()
    has_korean = False
    korean_count = 0

    for el in elements:
        if isinstance(el, SectionHeader):
            components.add(el.section_type)
        elif isinstance(el, NumberedParagraph):
            if el.is_korean_addition:
                has_korean = True
                korean_count += 1

    return sorted(components), has_korean, korean_count


def render_markdown(
    elements: list[IRElement],
    footnotes: dict[int, Footnote],
) -> str:
    """IR 요소 리스트를 구조 보존 마크다운으로 렌더링."""
    lines: list[str] = []
    all_footnote_ids: set[int] = set()

    # 1-pass: 통계 수집 (프론트매터용)
    components_present, has_korean, korean_count = _collect_render_stats(elements)

    # MetaInfo 추출
    meta: MetaInfo | None = None
    for el in elements:
        if isinstance(el, MetaInfo):
            meta = el
            break

    # base_authority: 개념체계(3), 실무서(4)는 섹션 authority를 오버라이드
    base_authority = meta.base_authority if meta else 1

    for el in elements:
        if isinstance(el, MetaInfo):
            # YAML 프론트매터
            lines.append("---")
            lines.append(f'standard_id: "{el.display_id}"')
            if el.standard_number:
                lines.append(f'standard_number: "{el.standard_number}"')
            lines.append(f'title: "{el.standard_title}"')
            if el.standard_type:
                lines.append(f'standard_type: "{el.standard_type}"')
            if el.standard_family:
                lines.append(f'standard_family: "{el.standard_family}"')
            if el.original_number:
                lines.append(f'original_number: "{el.original_number}"')
            lines.append(f"base_authority: {el.base_authority}")
            if el.last_amended_year:
                lines.append(f'last_amended_year: "{el.last_amended_year}"')
            if components_present:
                lines.append(f'components: [{", ".join(components_present)}]')
            lines.append(f"has_korean_additions: {'true' if has_korean else 'false'}")
            if korean_count > 0:
                lines.append(f"korean_paragraph_count: {korean_count}")
            lines.append("---")
            lines.append("")
            lines.append(f"# {el.display_id} {el.standard_title}")
            lines.append("")

        elif isinstance(el, SectionHeader):
            prefix = "#" * el.level
            lines.append(f"{prefix} {el.text}")
            if el.level == 2:
                component = el.section_type
                authority = _SECTION_AUTHORITY.get(el.section_type, 1)
                if base_authority > 1 and authority == 1:
                    authority = base_authority
                lines.append(f"<!-- component: {component} | authority: {authority} -->")
            lines.append("")

        elif isinstance(el, AuthorityMarker):
            if el.is_authoritative:
                lines.append(f"*{el.text}*")
                lines.append("<!-- authority_declaration: authoritative -->")
            else:
                lines.append(f"*{el.text}*")
                lines.append("<!-- authority_declaration: non-authoritative -->")
            lines.append("")

        elif isinstance(el, NumberedParagraph):
            # 서식 적용된 content
            if el.runs:
                formatted_content = _runs_to_markdown(el.runs, el.is_fully_bold)
            else:
                formatted_content = el.content

            # 각주 참조 추가
            formatted_content = _append_footnote_refs(
                formatted_content, el.footnote_refs
            )
            all_footnote_ids.update(el.footnote_refs)

            # 문단 렌더링
            if el.is_fully_bold:
                line = f"**{el.para_number}\t{formatted_content}**"
            else:
                line = f"{el.para_number}\t{formatted_content}"

            lines.append(line)

            # 메타데이터 코멘트
            meta_parts = [f"para: {el.para_number}"]
            if el.is_fully_bold:
                meta_parts.append("bold_para")
            if el.is_korean_addition:
                meta_parts.append("korean_addition")
            lines.append(f"<!-- {' | '.join(meta_parts)} -->")

            # 호/목
            for si in el.sub_items:
                si_content = si.content
                if si.runs:
                    si_content = _runs_to_markdown(si.runs, False)
                if si_content.startswith(si.marker):
                    si_content = si_content[len(si.marker):].lstrip()
                si_content = _append_footnote_refs(si_content, si.footnote_refs)
                all_footnote_ids.update(si.footnote_refs)
                lines.append(f"\t{si.marker}\t{si_content}")

                for ssi in si.sub_sub_items:
                    ssi_content = ssi.content
                    if ssi.runs:
                        ssi_content = _runs_to_markdown(ssi.runs, False)
                    if ssi_content.startswith(ssi.marker):
                        ssi_content = ssi_content[len(ssi.marker):].lstrip()
                    ssi_content = _append_footnote_refs(
                        ssi_content, ssi.footnote_refs
                    )
                    all_footnote_ids.update(ssi.footnote_refs)
                    lines.append(f"\t\t{ssi.marker}\t{ssi_content}")

            lines.append("")

        elif isinstance(el, ContinuationText):
            if el.runs:
                formatted = _runs_to_markdown(el.runs, el.is_fully_bold)
            else:
                formatted = el.content

            formatted = _append_footnote_refs(formatted, el.footnote_refs)
            all_footnote_ids.update(el.footnote_refs)

            if el.is_fully_bold:
                lines.append(f"**{formatted}**")
            else:
                lines.append(formatted)
            lines.append("")

        elif isinstance(el, ContentTable):
            if not el.headers:
                continue
            n = max(len(el.headers),
                    max((len(r) for r in el.rows), default=0))
            hdrs = (el.headers + [""] * n)[:n]
            lines.append("| " + " | ".join(hdrs) + " |")
            lines.append("| " + " | ".join(["---"] * n) + " |")
            for row in el.rows:
                padded = (row + [""] * n)[:n]
                lines.append("| " + " | ".join(padded) + " |")
            lines.append("")

    # 각주 섹션
    if footnotes and all_footnote_ids:
        lines.append("---")
        lines.append("")
        for fid in sorted(all_footnote_ids):
            fn = footnotes.get(fid)
            if fn:
                lines.append(f"[^{fid}]: {fn.content}")
        lines.append("")

    return "\n".join(lines)
