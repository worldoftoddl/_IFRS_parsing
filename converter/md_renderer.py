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
    SubItem,
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

_SECTION_COMPONENT: dict[str, str] = {
    "main": "main",
    "definitions": "definitions",
    "ag": "ag",
    "transition": "transition",
    "ie": "ie",
    "bc": "bc",
}


# ---------------------------------------------------------------------------
# run → 서식 마크다운 변환
# ---------------------------------------------------------------------------


def _runs_to_markdown(runs: list[FormattedRun], is_fully_bold: bool) -> str:
    """FormattedRun 리스트를 마크다운 서식 텍스트로 변환.

    is_fully_bold가 True이면 전체를 **로 감싸므로 개별 bold 마킹 생략.
    """
    if not runs:
        return ""

    parts: list[str] = []
    for run in runs:
        text = run.text
        if not text:
            continue

        # 탭/줄바꿈은 서식 적용하지 않음
        if text.strip() == "":
            parts.append(text)
            continue

        if is_fully_bold:
            # 전체 bold이므로 italic만 처리
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

    result = "".join(parts)

    # 연속 마커 정리: **text1****text2** → **text1text2**
    result = result.replace("****", "")
    result = result.replace("****** ", " ***")
    result = result.replace("** **", " ")
    # italic 연속 정리
    result = result.replace("**", "")  # 이건 너무 공격적

    # 다시 생각: 단순 join 후 연속 마커만 정리
    # 위의 접근이 위험하므로 다른 방식으로...

    return result


def _runs_to_markdown_v2(runs: list[FormattedRun], is_fully_bold: bool) -> str:
    """FormattedRun 리스트를 마크다운 서식 텍스트로 변환 (v2: 안전한 구현)."""
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


def render_markdown(
    elements: list[IRElement],
    footnotes: dict[int, Footnote],
) -> str:
    """IR 요소 리스트를 구조 보존 마크다운으로 렌더링."""
    lines: list[str] = []
    current_authority: int = 1
    all_footnote_ids: set[int] = set()

    for el in elements:
        if isinstance(el, MetaInfo):
            # YAML 프론트매터
            lines.append("---")
            lines.append(f'standard_id: "{el.display_id}"')
            if el.standard_number:
                lines.append(f'standard_number: "{el.standard_number}"')
            lines.append(f'title: "{el.standard_title}"')
            lines.append("---")
            lines.append("")
            lines.append(f"# {el.display_id} {el.standard_title}")
            lines.append("")

        elif isinstance(el, SectionHeader):
            prefix = "#" * el.level
            component = _SECTION_COMPONENT.get(el.section_type, el.section_type)
            authority = _SECTION_AUTHORITY.get(el.section_type, 1)
            current_authority = authority
            lines.append(f"{prefix} {el.text}")
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
                formatted_content = _runs_to_markdown_v2(el.runs, el.is_fully_bold)
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
                    si_content = _runs_to_markdown_v2(si.runs, False)
                si_content = _append_footnote_refs(si_content, si.footnote_refs)
                all_footnote_ids.update(si.footnote_refs)
                lines.append(f"\t{si.marker}\t{si_content}")

                for ssi in si.sub_sub_items:
                    ssi_content = ssi.content
                    if ssi.runs:
                        ssi_content = _runs_to_markdown_v2(ssi.runs, False)
                    ssi_content = _append_footnote_refs(
                        ssi_content, ssi.footnote_refs
                    )
                    all_footnote_ids.update(ssi.footnote_refs)
                    lines.append(f"\t\t{ssi.marker}\t{ssi_content}")

            lines.append("")

        elif isinstance(el, ContinuationText):
            if el.runs:
                formatted = _runs_to_markdown_v2(el.runs, el.is_fully_bold)
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
            n = len(el.headers)
            lines.append("| " + " | ".join(el.headers) + " |")
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
