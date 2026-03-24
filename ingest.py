"""K-IFRS 구조 보존 마크다운 → 벡터 DB 적재 CLI (Stage 2).

Usage:
    python ingest.py --parse-only              # 파싱만 (DB/API 불필요)
    python ingest.py --parse-only --single "K-IFRS 1115"  # 단일 기준서
"""

import argparse
import traceback
from collections import defaultdict
from pathlib import Path

from ingester.link_extractor import extract_links
from ingester.md_parser import parse_markdown_file
from ingester.summary_builder import build_summary


def process_all(
    md_dir: str = "output/md",
    parse_only: bool = True,
    single_standard: str | None = None,
) -> None:
    """전체 배치 처리."""
    md_path = Path(md_dir)
    files = sorted(md_path.rglob("*.md"))

    if not files:
        print(f"마크다운 파일을 찾을 수 없음: {md_dir}")
        return

    print(f"Processing {len(files)} markdown files")

    total_chunks = 0
    total_footnotes = 0
    total_links = 0
    total_summaries = 0
    component_dist: dict[str, int] = defaultdict(int)
    authority_dist: dict[int, int] = defaultdict(int)
    link_coverage: list[tuple[str, int, int, int, int]] = []  # (id, bc_total, bc_linked, ie_total, ie_linked)
    failures: list[tuple[str, str]] = []

    for f in files:
        try:
            standard, chunks, footnotes = parse_markdown_file(f)

            if single_standard and standard.standard_id != single_standard:
                continue

            # 참조 링크 추출
            links = extract_links(standard.standard_id, chunks)

            # 기준서 요약 생성
            summary = build_summary(standard, chunks)

            # 통계
            total_chunks += len(chunks)
            total_footnotes += len(footnotes)
            total_links += len(links)
            total_summaries += 1
            for c in chunks:
                component_dist[c.component] += 1
                authority_dist[c.authority] += 1

            # 링크 커버리지
            bc_total = len([c for c in chunks
                           if c.component == "bc"
                           or (c.para_number and c.para_number.startswith("BC"))])
            ie_total = len([c for c in chunks
                           if c.para_number and c.para_number.startswith("IE")])
            bc_linked = len(set(
                l.source_chunk_id for l in links if l.source_component == "bc"
            ))
            ie_linked = len(set(
                l.source_chunk_id for l in links if l.source_component == "ie"
            ))
            link_coverage.append((
                standard.standard_id, bc_total, bc_linked, ie_total, ie_linked
            ))

            scope_len = len(summary.scope_text)
            print(f"\n[{standard.standard_id}] {standard.title}")
            print(f"  chunks={len(chunks)}, links={len(links)}, "
                  f"footnotes={len(footnotes)}, scope={scope_len}ch")

            if not parse_only:
                # TODO: Phase 2/3에서 DB 삽입 + 임베딩
                pass

        except Exception as e:
            print(f"\n[ERROR] {f.name}: {e}")
            traceback.print_exc()
            failures.append((f.name, str(e)))

    # 전체 요약
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Files: {len(files)}, Failed: {len(failures)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Total links: {total_links}")
    print(f"  Total footnotes: {total_footnotes}")
    print(f"  Total summaries: {total_summaries}")
    print(f"\n  Component distribution:")
    for comp, count in sorted(component_dist.items()):
        print(f"    {comp}: {count}")
    print(f"\n  Authority distribution:")
    for auth, count in sorted(authority_dist.items()):
        print(f"    Level {auth}: {count}")

    # 링크 커버리지 요약
    bc_total_all = sum(x[1] for x in link_coverage)
    bc_linked_all = sum(x[2] for x in link_coverage)
    ie_total_all = sum(x[3] for x in link_coverage)
    ie_linked_all = sum(x[4] for x in link_coverage)
    print(f"\n  Link coverage:")
    print(f"    BC: {bc_linked_all}/{bc_total_all} "
          f"({bc_linked_all/max(1,bc_total_all):.0%})")
    print(f"    IE: {ie_linked_all}/{ie_total_all} "
          f"({ie_linked_all/max(1,ie_total_all):.0%})")

    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for name, err in failures:
            print(f"  {name}: {err}")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="K-IFRS 마크다운 → 벡터 DB 적재 (Stage 2)"
    )
    parser.add_argument("--parse-only", action="store_true",
                        help="파싱만 수행 (DB/API 불필요)")
    parser.add_argument("--single", help="단일 기준서 ID (예: 'K-IFRS 1115')")
    parser.add_argument("--md-dir", default="output/md", help="마크다운 디렉토리")
    args = parser.parse_args()

    process_all(
        md_dir=args.md_dir,
        parse_only=args.parse_only or True,
        single_standard=args.single,
    )
