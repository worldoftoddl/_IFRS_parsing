"""K-IFRS DOCX → 구조 보존 마크다운 변환 CLI.

Usage:
    uv run python convert.py                           # 전체 63개
    uv run python convert.py --single "IFRS_docx/..."  # 단일 파일
    uv run python convert.py --dry-run                 # 파싱+통계만
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from converter.docx_parser import parse_docx
from converter.md_renderer import render_markdown
from converter.models import MetaInfo

DOCX_DIR = Path("IFRS_docx")
OUTPUT_DIR = Path("output/md")


def process_single(docx_path: Path, output_dir: Path, dry_run: bool = False) -> dict:
    """단일 DOCX 파일 처리."""
    print(f"\n[{docx_path.name}]")

    elements, footnotes, stats = parse_docx(str(docx_path))
    meta = next((e for e in elements if isinstance(e, MetaInfo)), None)

    np = stats.get("numbered_paragraphs", 0)
    ct = stats.get("continuation_texts", 0)
    si = stats.get("sub_items", 0)
    orphan = stats.get("orphan_sub_items", 0)
    auth_markers = stats.get("authority_markers", 0)
    fn_count = stats.get("footnote_count", 0)

    print(f"  paragraphs={stats.get('total_paragraphs', 0)} "
          f"(numbered={np}, continuation={ct}, sub_items={si}, "
          f"filtered={stats.get('filtered_paragraphs', 0)}, "
          f"empty={stats.get('empty_paragraphs', 0)})")
    print(f"  tables={stats.get('total_tables', 0)} "
          f"(sections={stats.get('section_headers', 0)}, "
          f"content={stats.get('content_tables', 0)}, "
          f"revision={stats.get('revision_tables', 0)}, "
          f"meta={stats.get('meta_tables', 0)})")
    print(f"  authority_markers={auth_markers}, footnotes={fn_count}")

    # 스타일 분포
    style_dist = stats.get("style_distribution", {})
    total_paras = stats.get("total_paragraphs", 1)
    if style_dist:
        top3 = sorted(style_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_str = ", ".join(f"{k}:{v}({v/total_paras:.0%})" for k, v in top3)
        print(f"  styles top3: {top3_str}")

    # bold 문단 통계
    from converter.models import NumberedParagraph as NP, ContinuationText as CT
    bold_count = sum(
        1 for e in elements
        if (isinstance(e, NP) and e.is_fully_bold)
        or (isinstance(e, CT) and e.is_fully_bold)
    )
    korean_count = sum(
        1 for e in elements
        if isinstance(e, NP) and e.is_korean_addition
    )
    if bold_count:
        print(f"  bold_paragraphs={bold_count}")
    if korean_count:
        print(f"  korean_additions={korean_count}")

    # 경고
    total_content = np + ct + orphan
    null_ratio = (ct + orphan) / total_content if total_content else 0
    if null_ratio > 0.3:
        print(f"  WARNING: para_number null ratio={null_ratio:.1%}")
    if orphan > 0:
        print(f"  WARNING: orphan sub_items={orphan}")

    if dry_run:
        return stats

    # 마크다운 렌더링
    output_dir.mkdir(parents=True, exist_ok=True)
    md_text = render_markdown(elements, footnotes)
    md_path = output_dir / (docx_path.stem + ".md")
    md_path.write_text(md_text, encoding="utf-8")
    print(f"  → {md_path.name} ({len(md_text):,} chars)")

    return stats


def process_all(
    docx_dir: Path = DOCX_DIR,
    output_dir: Path = OUTPUT_DIR,
    dry_run: bool = False,
    single_file: str | None = None,
) -> None:
    """전체 배치 처리."""
    if single_file:
        files = [Path(single_file)]
    else:
        files = sorted(docx_dir.rglob("*.docx"))

    if not files:
        print(f"DOCX 파일을 찾을 수 없음: {docx_dir}")
        return

    mode = " (dry-run)" if dry_run else ""
    print(f"Processing {len(files)} DOCX files{mode}")

    all_stats: list[dict] = []
    failures: list[dict] = []

    for f in files:
        try:
            stats = process_single(f, output_dir, dry_run=dry_run)
            all_stats.append({"file": f.name, **stats})
        except Exception as e:
            print(f"  [ERROR] {e}")
            import traceback
            traceback.print_exc()
            failures.append({"file": f.name, "error": str(e)})

    # ---- 전체 요약 ----
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Success: {len(all_stats)}, Failed: {len(failures)}")

    if all_stats:
        total_np = sum(s.get("numbered_paragraphs", 0) for s in all_stats)
        total_ct = sum(s.get("continuation_texts", 0) for s in all_stats)
        total_si = sum(s.get("sub_items", 0) for s in all_stats)
        total_tbl = sum(s.get("content_tables", 0) for s in all_stats)
        total_sec = sum(s.get("section_headers", 0) for s in all_stats)
        total_fn = sum(s.get("footnote_count", 0) for s in all_stats)
        total_auth = sum(s.get("authority_markers", 0) for s in all_stats)

        print(f"  Numbered paragraphs: {total_np}")
        print(f"  Continuation texts:  {total_ct}")
        print(f"  Sub-items attached:  {total_si}")
        print(f"  Content tables:      {total_tbl}")
        print(f"  Section headers:     {total_sec}")
        print(f"  Footnotes:           {total_fn}")
        print(f"  Authority markers:   {total_auth}")

    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures:
            print(f"  {f['file']}: {f['error']}")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="K-IFRS DOCX → 구조 보존 마크다운 변환기"
    )
    parser.add_argument("--single", help="단일 DOCX 파일 경로")
    parser.add_argument("--dry-run", action="store_true",
                        help="파싱 + 통계만 (마크다운 생성 안 함)")
    parser.add_argument("--docx-dir", default=str(DOCX_DIR),
                        help="DOCX 디렉토리")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR),
                        help="출력 디렉토리")
    args = parser.parse_args()

    process_all(
        docx_dir=Path(args.docx_dir),
        output_dir=Path(args.output_dir),
        dry_run=args.dry_run,
        single_file=args.single,
    )
