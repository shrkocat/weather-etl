"""
Pipeline entry point.

Orchestrates: extract -> transform -> validate -> load, with logging and
error handling at each stage so a scheduled run (cron / Airflow / GitHub
Actions) fails loudly and clearly instead of silently doing nothing.

Usage:
    python -m src.main
    python -m src.main --skip-load          # dry run, no DB writes
    python -m src.main --dry-run            # alias for --skip-load
"""

import argparse
import sys
from datetime import datetime, timezone

from src.extract import extract_all, load_config, save_raw
from src.transform import transform, save_processed
from src.validate import validate
from src.load import load
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_pipeline(skip_load: bool = False) -> int:
    """
    Runs the full pipeline once. Returns process exit code (0 = success).
    """
    start = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info(f"Pipeline run started at {start.isoformat()}")

    try:
        config = load_config()

        # --- Extract ---
        logger.info("Stage 1/4: EXTRACT")
        raw_records = extract_all(config)
        if not raw_records:
            logger.error("Extract stage returned no data for any location. Aborting.")
            return 1
        save_raw(raw_records, config)

        # --- Transform ---
        logger.info("Stage 2/4: TRANSFORM")
        df = transform(raw_records)
        save_processed(df, config)

        # --- Validate ---
        logger.info("Stage 3/4: VALIDATE")
        result = validate(df, config)
        result.raise_if_invalid()

        # --- Load ---
        logger.info("Stage 4/4: LOAD")
        if skip_load:
            logger.info("Skipping load stage (--skip-load / --dry-run set).")
        else:
            rows_written = load(df, config)
            logger.info(f"Load complete: {rows_written} row(s) written.")

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(f"Pipeline run completed successfully in {elapsed:.1f}s")
        return 0

    except Exception:
        logger.exception("Pipeline run failed.")
        return 1


def parse_args():
    parser = argparse.ArgumentParser(description="Weather ETL pipeline")
    parser.add_argument(
        "--skip-load", "--dry-run",
        dest="skip_load",
        action="store_true",
        help="Run extract/transform/validate but don't write to the database.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = run_pipeline(skip_load=args.skip_load)
    sys.exit(exit_code)
