"""
validate.py — Data profiling and validation module for the NYC TLC pipeline.

Philosophy:
  - We NEVER silently fix data.  Every rejection is logged with a reason code
    so that downstream consumers (and the business) can audit what was dropped.
  - Validation rules are business-oriented, not just "is it not null".
  - The validation report written to disk is part of the pipeline's audit trail.

Validation rules (all configurable via config.py):
  VR-01  Duration:   1 min <= trip_duration <= 300 min
  VR-02  Distance:   0.1 mi <= trip_distance <= 200 mi
  VR-03  Speed:      5 mph <= avg_speed_mph <= 80 mph  (derived field)
  VR-04  Fare:       fare_amount > 0  (zero/negative fare → separate status)
  VR-05  Passengers: 1 <= passenger_count <= 6
  VR-06  Vendor:     VendorID in {1, 2}
  VR-07  Timestamps: pickup < dropoff; both within plausible calendar range
  VR-08  Locations:  PULocationID and DOLocationID must be non-null integers > 0
"""

import logging
from typing import Tuple

import pandas as pd

from config import (
    MIN_DURATION_MINUTES, MAX_DURATION_MINUTES,
    MIN_DISTANCE_MILES,   MAX_DISTANCE_MILES,
    MIN_SPEED_MPH,        MAX_SPEED_MPH,
    MIN_PASSENGERS,       MAX_PASSENGERS,
    MIN_FARE,
    VALID_VENDOR_IDS,
    VALIDATION_CSV,
)

logger = logging.getLogger(__name__)

# ── Profiling ──────────────────────────────────────────────────────────────────

def profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a column-level profiling report.

    For each column returns: dtype, null_count, null_pct, unique_count,
    min, max, and mean (for numeric columns).

    This is logged and also returned as a DataFrame so the notebook can
    display it.
    """
    rows = []
    for col in df.columns:
        null_ct = df[col].isna().sum()
        null_pct = 100.0 * null_ct / len(df) if len(df) else 0.0
        try:
            unique_ct = df[col].nunique()
        except TypeError:
            unique_ct = None

        row = {
            "column":      col,
            "dtype":       str(df[col].dtype),
            "null_count":  int(null_ct),
            "null_pct":    round(null_pct, 2),
            "unique_count": unique_ct,
        }

        if pd.api.types.is_numeric_dtype(df[col]):
            row["min"]  = float(df[col].min())  if null_ct < len(df) else None
            row["max"]  = float(df[col].max())  if null_ct < len(df) else None
            row["mean"] = float(df[col].mean()) if null_ct < len(df) else None
        else:
            row["min"] = row["max"] = row["mean"] = None

        rows.append(row)

    profile = pd.DataFrame(rows)
    logger.info("[VALIDATE] Profiling complete for %d columns.", len(profile))
    return profile


# ── Derived columns ────────────────────────────────────────────────────────────

def _add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add duration_minutes and avg_speed_mph before applying rules."""
    df = df.copy()

    # Ensure datetime types
    df["tpep_pickup_datetime"]  = pd.to_datetime(df["tpep_pickup_datetime"],  errors="coerce")
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"], errors="coerce")

    # Duration in minutes
    df["duration_minutes"] = (
        (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"])
        .dt.total_seconds() / 60.0
    )

    # Average speed in mph (distance / duration_hours)
    duration_hours = df["duration_minutes"] / 60.0
    # Avoid division by zero
    df["avg_speed_mph"] = df["trip_distance"] / duration_hours.replace(0, float("nan"))

    return df


# ── Validation ─────────────────────────────────────────────────────────────────

def validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply all validation rules.

    Returns
    -------
    valid_df   : DataFrame with only validated rows, plus a
                 `validation_status` column set to "VALID".
    reject_df  : DataFrame of rejected rows with `rejection_reason` and
                 `validation_status` columns explaining why each was dropped.

    Design note:
        A row can fail multiple rules.  We collect ALL rule failures for each
        row and concatenate them into the rejection_reason string, separated
        by " | ".  This is more useful for debugging than stopping at the
        first failure.
    """
    logger.info("[VALIDATE] Starting validation on %d rows …", len(df))

    df = _add_derived_columns(df)

    # Accumulate a list of failure reason strings per row
    failure_reasons = pd.Series([""] * len(df), index=df.index, dtype=str)

    def _flag(mask: pd.Series, code: str) -> None:
        """Add *code* to failure_reasons where *mask* is True."""
        failure_reasons[mask] = failure_reasons[mask].apply(
            lambda x: (x + " | " + code) if x else code
        )

    # VR-01: Duration
    bad_duration = (
        df["duration_minutes"].isna() |
        (df["duration_minutes"] < MIN_DURATION_MINUTES) |
        (df["duration_minutes"] > MAX_DURATION_MINUTES)
    )
    _flag(bad_duration, f"VR-01:DURATION_OUT_OF_RANGE[{MIN_DURATION_MINUTES},{MAX_DURATION_MINUTES}]min")

    # VR-02: Distance
    bad_distance = (
        df["trip_distance"].isna() |
        (df["trip_distance"] < MIN_DISTANCE_MILES) |
        (df["trip_distance"] > MAX_DISTANCE_MILES)
    )
    _flag(bad_distance, f"VR-02:DISTANCE_OUT_OF_RANGE[{MIN_DISTANCE_MILES},{MAX_DISTANCE_MILES}]mi")

    # VR-03: Speed
    bad_speed = (
        df["avg_speed_mph"].isna() |
        (df["avg_speed_mph"] < MIN_SPEED_MPH) |
        (df["avg_speed_mph"] > MAX_SPEED_MPH)
    )
    _flag(bad_speed, f"VR-03:SPEED_OUT_OF_RANGE[{MIN_SPEED_MPH},{MAX_SPEED_MPH}]mph")

    # VR-04: Fare
    zero_fare = df["fare_amount"].notna() & (df["fare_amount"] == 0.0)
    neg_fare  = df["fare_amount"].notna() & (df["fare_amount"] < 0.0)
    null_fare = df["fare_amount"].isna()
    _flag(zero_fare, "VR-04:ZERO_FARE")
    _flag(neg_fare,  "VR-04:NEGATIVE_FARE")
    _flag(null_fare, "VR-04:NULL_FARE")

    # VR-05: Passengers
    bad_pax = (
        df["passenger_count"].isna() |
        (df["passenger_count"] < MIN_PASSENGERS) |
        (df["passenger_count"] > MAX_PASSENGERS)
    )
    _flag(bad_pax, f"VR-05:PASSENGER_COUNT_INVALID[{MIN_PASSENGERS},{MAX_PASSENGERS}]")

    # VR-06: Vendor
    bad_vendor = ~df["VendorID"].isin(VALID_VENDOR_IDS)
    _flag(bad_vendor, f"VR-06:UNKNOWN_VENDOR(not in {sorted(VALID_VENDOR_IDS)})")

    # VR-07: Timestamps — pickup must be before dropoff
    bad_ts = (
        df["tpep_pickup_datetime"].isna() |
        df["tpep_dropoff_datetime"].isna() |
        (df["tpep_pickup_datetime"] >= df["tpep_dropoff_datetime"])
    )
    _flag(bad_ts, "VR-07:TIMESTAMP_INVALID(pickup>=dropoff or null)")

    # VR-07b: Timestamps — must be in 2024 (data currency check)
    wrong_year = (
        (df["tpep_pickup_datetime"].dt.year != 2024) &
        df["tpep_pickup_datetime"].notna()
    )
    _flag(wrong_year, "VR-07b:TIMESTAMP_WRONG_YEAR(expected 2024)")

    # VR-08: Locations
    bad_loc = (
        df["PULocationID"].isna() | (df["PULocationID"] <= 0) |
        df["DOLocationID"].isna() | (df["DOLocationID"] <= 0)
    )
    _flag(bad_loc, "VR-08:INVALID_LOCATION_ID")

    # ── Split into valid / rejected ───────────────────────────────────────────
    is_rejected = failure_reasons != ""

    reject_df = df[is_rejected].copy()
    reject_df["rejection_reason"]  = failure_reasons[is_rejected]
    reject_df["validation_status"] = reject_df["rejection_reason"].apply(
        lambda r: "ZERO_FARE" if r == "VR-04:ZERO_FARE" else
                  "NEGATIVE_FARE" if r == "VR-04:NEGATIVE_FARE" else
                  "REJECTED"
    )

    valid_df = df[~is_rejected].copy()
    valid_df["validation_status"] = "VALID"

    logger.info(
        "[VALIDATE] Results: %d valid (%.1f%%), %d rejected (%.1f%%)",
        len(valid_df), 100 * len(valid_df) / len(df),
        len(reject_df), 100 * len(reject_df) / len(df)
    )

    # Log breakdown by rejection reason
    if len(reject_df) > 0:
        # Expand pipe-separated reasons and count occurrences
        all_reasons = (
            reject_df["rejection_reason"]
            .str.split(" | ")
            .explode()
            .value_counts()
        )
        logger.info("[VALIDATE] Rejection breakdown:\n%s", all_reasons.to_string())

    return valid_df, reject_df


def save_validation_log(reject_df: pd.DataFrame) -> None:
    """
    Write the rejection log to outputs/validation_log.csv.

    Columns preserved: all original trip columns + rejection_reason + validation_status.
    This is the audit trail that the Compliance Officer can inspect.
    """
    cols_to_save = [
        "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
        "trip_distance", "fare_amount", "PULocationID", "DOLocationID",
        "duration_minutes", "avg_speed_mph",
        "rejection_reason", "validation_status"
    ]
    # Only include columns that actually exist
    cols_to_save = [c for c in cols_to_save if c in reject_df.columns]
    reject_df[cols_to_save].to_csv(VALIDATION_CSV, index=False)
    logger.info("[VALIDATE] Rejection log written to %s (%d rows).", VALIDATION_CSV, len(reject_df))
