"""K-IFRS 구조 보존 마크다운 → 벡터 DB 적재 CLI (Stage 2).

Usage:
    python ingest.py --export-json                     # JSON 내보내기 (검수용)
    python ingest.py --parse-only                      # 파싱 통계만
    python ingest.py --skip-embedding                  # DB 삽입 (임베딩 NULL)
    python ingest.py                                   # 전체 (파싱+임베딩+DB)
    python ingest.py --single "K-IFRS 1115"            # 단일 기준서
"""

import argparse
import json
import traceback
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from ingester.chunk_splitter import split_oversized_chunks
from ingester.config import Config
from ingester.link_extractor import extract_links
from ingester.md_parser import parse_markdown_file
from ingester.summary_builder import build_summary


def _normalize_id(standard_id: str) -> str:
    """'K-IFRS 1115' → 'KIFRS1115'"""
    import re
    return re.sub(r"[^A-Za-z0-9가-힣]", "", standard_id)


def export_json(
    config: Config,
    single_standard: str | None = None,
) -> None:
    """청크를 기준서별 JSON으로 내보내기."""
    md_path = Path(config.md_dir)
    files = sorted(md_path.rglob("*.md"))
    out_dir = Path("output/search_chunks")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Exporting {len(files)} files to {out_dir}/")

    # 전체 통계
    token_buckets = {"0-100": 0, "100-500": 0, "500-1000": 0,
                     "1000-2000": 0, "2000-4000": 0, "4000+": 0}
    oversized: list[dict] = []
    total_chunks = 0
    total_standards = 0

    for f in files:
        try:
            standard, chunks, footnotes = parse_markdown_file(f)

            if single_standard and standard.standard_id != single_standard:
                continue

            chunks = split_oversized_chunks(chunks)
            links = extract_links(standard.standard_id, chunks)
            summary = build_summary(standard, chunks)

            search_chunks = [c for c in chunks if c.component != "definitions"]
            standard.total_chunks = len(search_chunks)
            total_standards += 1
            total_chunks += len(search_chunks)

            # 토큰 분포 집계 (검색 대상 청크만)
            for c in search_chunks:
                t = c.token_estimate
                if t < 100:
                    token_buckets["0-100"] += 1
                elif t < 500:
                    token_buckets["100-500"] += 1
                elif t < 1000:
                    token_buckets["500-1000"] += 1
                elif t < 2000:
                    token_buckets["1000-2000"] += 1
                elif t < 4000:
                    token_buckets["2000-4000"] += 1
                else:
                    token_buckets["4000+"] += 1
                    oversized.append({
                        "chunk_id": c.chunk_id,
                        "standard_id": c.standard_id,
                        "para_number": c.para_number,
                        "char_count": c.char_count,
                        "token_estimate": c.token_estimate,
                    })

            # 기준서별 JSON (검색 대상 청크만)
            nid = _normalize_id(standard.standard_id)
            data = {
                "standard": asdict(standard),
                "summary": asdict(summary),
                "chunks": [asdict(c) for c in search_chunks],
                "links": [asdict(l) for l in links],
                "footnotes": [asdict(fn) for fn in footnotes],
            }
            json_path = out_dir / f"{nid}.json"
            json_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  [{standard.standard_id}] {len(chunks)} chunks → {json_path.name}")

        except Exception as e:
            print(f"  [ERROR] {f.name}: {e}")
            traceback.print_exc()

    # 전체 통계 JSON
    summary_data = {
        "total_standards": total_standards,
        "total_chunks": total_chunks,
        "token_distribution": token_buckets,
        "oversized_chunks": oversized,
    }
    summary_path = out_dir / "_summary.json"
    summary_path.write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n{'='*70}")
    print(f"Total: {total_standards} standards, {total_chunks} chunks")
    print(f"Token distribution: {token_buckets}")
    print(f"Oversized (4000+): {len(oversized)} chunks")
    if oversized:
        for o in oversized:
            print(f"  {o['chunk_id']} ({o['token_estimate']} tokens)")
    print(f"\nExported to {out_dir}/")


def process_all(
    config: Config,
    parse_only: bool = False,
    skip_embedding: bool = False,
    single_standard: str | None = None,
) -> None:
    """전체 배치 처리."""
    md_path = Path(config.md_dir)
    files = sorted(md_path.rglob("*.md"))

    if not files:
        print(f"마크다운 파일을 찾을 수 없음: {config.md_dir}")
        return

    db = None
    embedder = None

    if not parse_only:
        from ingester.db_writer import DBWriter
        db = DBWriter(config.db_url)
        db.init_schema()
        print("DB schema initialized.")

        if not skip_embedding:
            from ingester.embedder import Embedder
            embedder = Embedder(config)
            print(f"Embedder ready: {config.embedding_model}")

    print(f"\nProcessing {len(files)} markdown files")
    mode = " (parse-only)" if parse_only else " (skip-embedding)" if skip_embedding else ""
    print(f"Mode:{mode or ' full pipeline'}")

    total_chunks = 0
    total_links = 0
    total_footnotes = 0
    component_dist: dict[str, int] = defaultdict(int)
    authority_dist: dict[int, int] = defaultdict(int)
    failures: list[tuple[str, str]] = []

    for f in files:
        try:
            standard, chunks, footnotes = parse_markdown_file(f)

            if single_standard and standard.standard_id != single_standard:
                continue

            chunks = split_oversized_chunks(chunks)
            links = extract_links(standard.standard_id, chunks)
            summary = build_summary(standard, chunks)

            # 정의 청크는 summary에 포함되므로 임베딩/검색 대상에서 제외
            search_chunks = [c for c in chunks if c.component != "definitions"]
            standard.total_chunks = len(search_chunks)

            total_chunks += len(search_chunks)
            total_links += len(links)
            total_footnotes += len(footnotes)
            for c in search_chunks:
                component_dist[c.component] += 1
                authority_dist[c.authority] += 1

            def_count = len(chunks) - len(search_chunks)
            print(f"\n[{standard.standard_id}] {standard.title}")
            print(f"  chunks={len(search_chunks)}, definitions={def_count}, "
                  f"links={len(links)}, footnotes={len(footnotes)}")

            if parse_only:
                continue

            db.upsert_standard(standard)
            db.upsert_footnotes(footnotes)
            db.upsert_links(links)

            chunk_embeddings = None
            summary_embedding = None
            if embedder:
                texts = [c.content_text for c in search_chunks]
                print(f"  Embedding {len(texts)} chunks...", end="", flush=True)
                chunk_embeddings = embedder.embed_batch(texts)
                summary_embedding = embedder.embed_single(summary.scope_text)
                print(" done.")

            db.upsert_chunks(search_chunks, chunk_embeddings)
            db.upsert_summary(summary, summary_embedding)

        except Exception as e:
            print(f"\n[ERROR] {f.name}: {e}")
            traceback.print_exc()
            failures.append((f.name, str(e)))

    if db and embedder and not single_standard:
        db.create_vector_indexes()

    if db:
        db.close()

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"  Files: {len(files)}, Failed: {len(failures)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Total links: {total_links}")
    print(f"  Total footnotes: {total_footnotes}")
    print(f"\n  Component distribution:")
    for comp, count in sorted(component_dist.items()):
        print(f"    {comp}: {count}")
    print(f"\n  Authority distribution:")
    for auth, count in sorted(authority_dist.items()):
        print(f"    Level {auth}: {count}")

    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for name, err in failures:
            print(f"  {name}: {err}")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="K-IFRS 마크다운 → 벡터 DB 적재 (Stage 2)"
    )
    parser.add_argument("--export-json", action="store_true",
                        help="JSON 내보내기 (청크 검수용)")
    parser.add_argument("--parse-only", action="store_true",
                        help="파싱 통계만")
    parser.add_argument("--skip-embedding", action="store_true",
                        help="DB 삽입만 (임베딩 NULL)")
    parser.add_argument("--single", help="단일 기준서 ID (예: 'K-IFRS 1115')")
    parser.add_argument("--md-dir", default=None, help="마크다운 디렉토리")
    args = parser.parse_args()

    cfg = Config.from_env()
    if args.md_dir:
        cfg.md_dir = args.md_dir

    if args.export_json:
        export_json(cfg, single_standard=args.single)
    else:
        process_all(
            config=cfg,
            parse_only=args.parse_only,
            skip_embedding=args.skip_embedding,
            single_standard=args.single,
        )
