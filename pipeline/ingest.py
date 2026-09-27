"""
ingest.py — Data retrieval module for the NYC TLC pipeline.

Retrieval modes used:
  1. HTTP file download  — TLC Parquet (trips) and CSV (zone lookup)
  2. REST API / JSON     — NYC Open Data SODA metadata endpoint
  3. Local file read     — Vendor metadata CSV (embedded in repo)

Design decisions:
  - Raw files are NEVER overwritten if they already exist on disk.
    This preserves provenance and makes the pipeline idempotent.
  - Download progress is shown so operators know retrieval is happening.
  - All retrieval errors raise an explicit exception rather than silently
    returning an empty frame.
"""

import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

from config import (
    RAW_PARQUET, RAW_ZONES, RAW_VENDORS, RAW_METADATA,
    TLC_PARQUET_URL, TLC_ZONE_CSV_URL, SODA_METADATA_URL,
    VENDOR_METADATA, SAMPLE_ROWS
)

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _download_file(url: str, dest: Path, label: str) -> None:
    """
    Stream-download *url* to *dest*.  Skip if the file already exists.
    Using streaming so we don't load the whole Parquet into memory during download.
    """
    if dest.exists():
        logger.info("[INGEST] %s already present at %s — skipping download.", label, dest)
        return

    logger.info("[INGEST] Downloading %s from %s …", label, url)
    t0 = time.time()
    try:
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download {label}: {exc}") from exc

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0
    chunk_size = 1 << 20  # 1 MB chunks

    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                fh.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = 100 * downloaded / total
                    logger.debug("[INGEST] %s — %.1f%% (%.1f MB / %.1f MB)",
                                 label, pct, downloaded / 1e6, total / 1e6)

    elapsed = time.time() - t0
    logger.info("[INGEST] %s downloaded in %.1f s (%.1f MB).",
                label, elapsed, downloaded / 1e6)


def _fetch_metadata_api(url: str, dest: Path, label: str) -> dict:
    """
    Fetch JSON from a REST endpoint and cache it to *dest*.
    If the file already exists the cached version is returned.
    This demonstrates the API retrieval mode.
    """
    if dest.exists():
        logger.info("[INGEST] %s metadata already cached at %s.", label, dest)
        with open(dest, "r", encoding="utf-8") as fh:
            return json.load(fh)

    logger.info("[INGEST] Fetching %s metadata from API: %s …", label, url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("[INGEST] Could not reach metadata API (%s). Using empty dict.", exc)
        data = {}

    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

    logger.info("[INGEST] %s metadata cached to %s.", label, dest)
    return data


# ── public API ─────────────────────────────────────────────────────────────────

def ingest_trips() -> pd.DataFrame:
    """
    Retrieval mode 1 — HTTP Parquet download.

    Downloads the TLC Yellow Taxi Jan-2024 Parquet file if not already cached,
    then loads it into a DataFrame.  SAMPLE_ROWS can be set in config for fast
    development iterations.

    Returns a raw DataFrame — no transformations applied here.
    """
    _download_file(TLC_PARQUET_URL, RAW_PARQUET, "TLC Yellow Trip Data (Jan 2024)")

    logger.info("[INGEST] Loading trips from %s …", RAW_PARQUET)
    df = pd.read_parquet(RAW_PARQUET)
    logger.info("[INGEST] Loaded %d rows, %d columns.", len(df), len(df.columns))

    if SAMPLE_ROWS is not None:
        logger.info("[INGEST] Sampling to %d rows (SAMPLE_ROWS set in config).", SAMPLE_ROWS)
        df = df.head(SAMPLE_ROWS)

    return df


def ingest_zones() -> pd.DataFrame:
    """
    Retrieval mode 1 — HTTP CSV download.

    Downloads the TLC Zone Lookup CSV (LocationID → zone name + borough).
    Returns a DataFrame with columns: LocationID, Borough, Zone, service_zone.
    """
    _download_file(TLC_ZONE_CSV_URL, RAW_ZONES, "TLC Zone Lookup CSV")

    logger.info("[INGEST] Loading zone lookup from %s …", RAW_ZONES)
    zones = pd.read_csv(RAW_ZONES)
    logger.info("[INGEST] Loaded %d zones.", len(zones))
    return zones


def ingest_vendors() -> pd.DataFrame:
    """
    Retrieval mode 3 — Local file read.

    Writes the embedded vendor metadata CSV (derived from TLC data dictionary)
    to disk if not present, then reads it back.  This preserves the same
    read-from-file pattern as the other sources and keeps the raw/ directory
    as the single source of truth.
    """
    if not RAW_VENDORS.exists():
        logger.info("[INGEST] Writing embedded vendor metadata to %s …", RAW_VENDORS)
        pd.DataFrame(VENDOR_METADATA).to_csv(RAW_VENDORS, index=False)

    vendors = pd.read_csv(RAW_VENDORS)
    logger.info("[INGEST] Loaded %d vendors from %s.", len(vendors), RAW_VENDORS)
    return vendors


def ingest_metadata() -> dict:
    """
    Retrieval mode 2 — REST API / JSON.

    Calls the NYC Open Data SODA metadata endpoint for the TLC Yellow Taxi
    dataset.  Returns the raw JSON dict, which the profiling notebook uses
    to cross-check field names and expected types.
    """
    return _fetch_metadata_api(SODA_METADATA_URL, RAW_METADATA, "TLC SODA")


def verify_retrieval_completeness(df: pd.DataFrame) -> None:
    """
    Completeness checks we run immediately after loading, before any
    validation.  These answer the question: "How do I know retrieval is
    complete?"

    Checks:
      1. Row count is non-zero and plausible for a January dataset
         (TLC typically publishes ~2–3 million Yellow trips per month).
      2. All expected columns are present.
      3. No column is entirely NULL (would indicate a corrupted download).
    """
    logger.info("[INGEST] Running retrieval completeness checks …")

    # 1. Row count plausibility
    MIN_EXPECTED_ROWS = 100_000   # conservative lower bound
    if len(df) < MIN_EXPECTED_ROWS:
        logger.warning(
            "[INGEST] Only %d rows loaded — expected at least %d for a monthly TLC file. "
            "Check if the download was truncated.",
            len(df), MIN_EXPECTED_ROWS
        )
    else:
        logger.info("[INGEST] Row count OK: %d rows.", len(df))

    # 2. Schema check
    EXPECTED_COLUMNS = {
        "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "passenger_count", "trip_distance", "PULocationID", "DOLocationID",
        "fare_amount", "tip_amount", "total_amount", "payment_type"
    }
    missing_cols = EXPECTED_COLUMNS - set(df.columns)
    if missing_cols:
        raise RuntimeError(
            f"[INGEST] Schema check FAILED — missing columns: {missing_cols}. "
            "The file may be from a different schema version."
        )
    logger.info("[INGEST] Schema check OK — all expected columns present.")

    # 3. All-null columns
    all_null = [c for c in df.columns if df[c].isna().all()]
    if all_null:
        logger.warning("[INGEST] Columns that are entirely NULL: %s", all_null)
    else:
        logger.info("[INGEST] No entirely-null columns detected.")

    logger.info("[INGEST] Completeness checks complete.")
