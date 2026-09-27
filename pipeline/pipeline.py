"""
pipeline.py — End-to-end runnable pipeline for the NYC TLC project.

Run with:
    python pipeline/pipeline.py

Design principles:
  - Ingest → Validate → Transform → Metrics output, in that order
  - Idempotent: running twice gives the same result (processed files overwritten, not appended)
  - Explicit logging at every step with timestamps and row counts
  - Failure handling: any unrecoverable error exits with code 1 and a clear message
  - Rerun behaviour: raw files are NOT re-downloaded if already present on disk
  - A plain-text log (outputs/pipeline_run.log) is written alongside the CSV outputs
    so operators can audit exactly what happened in a given run
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the pipeline/ directory to sys.path so we can import sibling modules
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import PIPELINE_LOG, METRICS_CSV, VALIDATION_CSV
from ingest import ingest_trips, ingest_zones, ingest_vendors, ingest_metadata, verify_retrieval_completeness
from validate import profile_dataframe, validate, save_validation_log
from transform import build_enriched_trips, calculate_metrics, save_outputs, print_metrics_summary


# ── Logging setup ──────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    """
    Configure logging to write to BOTH the console and the pipeline log file.

    The log file records everything at DEBUG level; the console shows INFO+.
    This means operators can see progress in real time, and the full trace
    is preserved for audit.
    """
    fmt = "%(asctime)s | %(levelname)-8s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler — INFO and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(ch)

    # File handler — DEBUG and above (full trace)
    fh = logging.FileHandler(PIPELINE_LOG, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(fh)


# ── Pipeline steps ─────────────────────────────────────────────────────────────

def step_ingest(logger: logging.Logger):
    """Step 1 — Retrieve all source data."""
    logger.info("=" * 60)
    logger.info("STEP 1 / 4 — INGEST")
    logger.info("=" * 60)

    trips_df  = ingest_trips()
    zones_df  = ingest_zones()
    vendors_df = ingest_vendors()
    _metadata = ingest_metadata()   # fetched for completeness; used in notebooks

    # Completeness checks — raises RuntimeError if schema is wrong
    verify_retrieval_completeness(trips_df)

    logger.info("STEP 1 complete. Raw trips: %d rows.", len(trips_df))
    return trips_df, zones_df, vendors_df


def step_validate(trips_df, logger: logging.Logger):
    """Step 2 — Profile and validate the raw trip data."""
    logger.info("=" * 60)
    logger.info("STEP 2 / 4 — PROFILE & VALIDATE")
    logger.info("=" * 60)

    # Profile before validation (for the record)
    profile = profile_dataframe(trips_df)
    logger.info("Profiling summary (null rates):\n%s",
                profile[["column", "null_pct"]].to_string(index=False))

    # Apply business rules
    valid_df, reject_df = validate(trips_df)

    # Save the rejection audit log
    save_validation_log(reject_df)

    logger.info(
        "STEP 2 complete. Valid: %d | Rejected: %d",
        len(valid_df), len(reject_df)
    )
    return valid_df, reject_df


def step_transform(valid_df, zones_df, vendors_df, logger: logging.Logger):
    """Step 3 — Enrich, model, and compute metrics."""
    logger.info("=" * 60)
    logger.info("STEP 3 / 4 — TRANSFORM & MODEL")
    logger.info("=" * 60)

    enriched_df = build_enriched_trips(valid_df, zones_df, vendors_df)
    metrics = calculate_metrics(enriched_df)
    save_outputs(enriched_df, metrics)

    logger.info("STEP 3 complete. Enriched trips: %d rows.", len(enriched_df))
    return enriched_df, metrics


def step_output(metrics, logger: logging.Logger):
    """Step 4 — Print human-readable summary and log file locations."""
    logger.info("=" * 60)
    logger.info("STEP 4 / 4 — OUTPUT")
    logger.info("=" * 60)

    print_metrics_summary(metrics)

    logger.info("Pipeline outputs:")
    logger.info("  Metrics report  : %s", METRICS_CSV)
    logger.info("  Validation log  : %s", VALIDATION_CSV)
    logger.info("  Pipeline log    : %s", PIPELINE_LOG)


# ── Entry point ────────────────────────────────────────────────────────────────

def run_pipeline() -> int:
    """
    Orchestrate all pipeline steps.

    Returns 0 on success, 1 on any unrecoverable failure.
    All exceptions are caught here so the exit code is always explicit.
    """
    _setup_logging()
    logger = logging.getLogger(__name__)

    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    t_start = time.time()

    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║  NYC TLC YELLOW TAXI PIPELINE — RUN %s ║", run_id)
    logger.info("╚══════════════════════════════════════════════════════╝")

    try:
        # Step 1
        trips_df, zones_df, vendors_df = step_ingest(logger)

        # Step 2
        valid_df, _reject_df = step_validate(trips_df, logger)

        # Step 3
        enriched_df, metrics = step_transform(valid_df, zones_df, vendors_df, logger)

        # Step 4
        step_output(metrics, logger)

    except RuntimeError as exc:
        logger.error("PIPELINE FAILED (unrecoverable): %s", exc)
        logger.error("Fix the issue above and re-run.  Partial outputs may exist.")
        return 1

    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user (KeyboardInterrupt).")
        return 1

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        return 1

    elapsed = time.time() - t_start
    logger.info(
        "Pipeline completed successfully in %.1f seconds. Run ID: %s",
        elapsed, run_id
    )
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
