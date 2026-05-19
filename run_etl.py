#!/usr/bin/env python3
"""
Command-line interface for the bibliometrix-python ETL pipeline.

Usage examples
--------------
File mode (auto-detect source):
    python run_etl.py --mode file --input sources/Scopus/Scopus.csv --output out/unified.csv

File mode (explicit source):
    python run_etl.py --mode file --source SCOPUS --input sources/Scopus/Scopus.csv

API mode (OpenAlex):
    python run_etl.py --mode api --platform openalex --query "machine learning" --max-records 200 --output out/oa.csv

API mode (PubMed):
    python run_etl.py --mode api --platform pubmed_api --query "CRISPR" --max-records 100
"""

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_etl")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_etl.py",
        description="bibliometrix-python ETL pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--mode",
        choices=["file", "api"],
        required=True,
        help="'file' for local files, 'api' for live API retrieval",
    )

    # File mode args
    p.add_argument("--input", metavar="PATH", help="Input file path (file mode)")
    p.add_argument(
        "--source",
        metavar="SOURCE",
        help="Explicit source override: SCOPUS | DIMENSIONS | PUBMED | WOS (file mode, optional)",
    )

    # API mode args
    p.add_argument(
        "--platform",
        choices=["openalex", "pubmed_api"],
        default="openalex",
        help="API platform: openalex (default) or pubmed_api",
    )
    p.add_argument("--query", metavar="QUERY", help="Search query string (API mode)")
    p.add_argument(
        "--max-records",
        type=int,
        default=100,
        metavar="N",
        dest="max_records",
        help="Maximum records to retrieve (API mode, default 100)",
    )

    # Shared
    p.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Output CSV path. If omitted, prints shape summary only.",
    )
    p.add_argument("--verbose", "-v", action="store_true", help="Enable DEBUG logging")
    return p


def _run_file(args) -> int:
    if not args.input:
        log.error("--input is required for --mode file")
        return 1

    from www.services.etl.pipeline import run_file_pipeline

    log.info("FILE mode — input: %s", args.input)
    try:
        df, is_valid, errors = run_file_pipeline(
            file_path=args.input,
            source=args.source,
            output_path=args.output,
        )
    except FileNotFoundError as exc:
        log.error("File not found: %s", exc)
        return 1
    except ValueError as exc:
        log.error("Error: %s", exc)
        return 1

    _print_summary(df, is_valid, errors, args.output)
    return 0 if is_valid else 2


def _run_api(args) -> int:
    if not args.query:
        log.error("--query is required for --mode api")
        return 1

    from www.services.etl.pipeline import run_api_pipeline

    log.info("API mode — platform: %s  query: %r  max_records: %d",
             args.platform, args.query, args.max_records)
    try:
        df, is_valid, errors = run_api_pipeline(
            query=args.query,
            platform=args.platform,
            output_path=args.output,
            max_records=args.max_records,
        )
    except ValueError as exc:
        log.error("Error: %s", exc)
        return 1

    _print_summary(df, is_valid, errors, args.output)
    return 0 if is_valid else 2


def _print_summary(df, is_valid, errors, output_path):
    print("\n" + "=" * 60)
    print(f"  Records : {len(df)}")
    print(f"  Columns : {len(df.columns)}")
    print(f"  Valid   : {'YES' if is_valid else 'NO'}")
    if errors:
        print(f"  Issues  : {len(errors)}")
        for err in errors[:5]:
            print(f"    • {err}")
        if len(errors) > 5:
            print(f"    … and {len(errors) - 5} more")
    if output_path:
        print(f"  Exported: {output_path}")
    print("=" * 60 + "\n")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.mode == "file":
        return _run_file(args)
    else:
        return _run_api(args)


if __name__ == "__main__":
    sys.exit(main())
