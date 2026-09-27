"""
transform.py — Workflow modelling and metric calculation for the NYC TLC pipeline.

This module:
  1. Joins validated trips to zone and vendor dimension tables.
  2. Calculates all 5 business metrics.
  3. Saves processed trips and the metrics report.

The 5 metrics (all linked to the primary KPI — Revenue per Zone per Month):

  M1  Revenue per Zone     — SUM(fare + tip) grouped by pickup_borough
  M2  Avg Duration by Hour — AVG(duration_minutes) by pickup_hour
  M3  Trip Count per Vendor— COUNT(*) by vendor_name
  M4  Speed Plausibility   — % trips with 5 <= avg_speed_mph <= 80
  M5  Fare per Mile        — MEDIAN(fare_amount / trip_distance) by borough
"""

import logging

import pandas as pd

from config import (
    MIN_SPEED_MPH, MAX_SPEED_MPH,
    PROCESSED_TRIPS, METRICS_CSV,
)

logger = logging.getLogger(__name__)


# ── Joins ──────────────────────────────────────────────────────────────────────

def build_enriched_trips(
    valid_df: pd.DataFrame,
    zones_df: pd.DataFrame,
    vendors_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join validated trip data to zone and vendor dimensions.

    Zone lookup is done twice:
      - Once for PULocationID → pickup_borough, pickup_zone
      - Once for DOLocationID → dropoff_borough, dropoff_zone

    Trips whose LocationID is not found in the zone table are retained
    (LEFT JOIN) but their borough/zone columns will be NaN — these are
    flagged in the output as "UNKNOWN_ZONE" so they remain visible in KPIs.

    Vendor join adds a human-readable vendor_name column.
    """
    logger.info("[TRANSFORM] Enriching %d validated trips with zone and vendor data …", len(valid_df))

    # Standardise zone column names for the join
    pu_zones = zones_df.rename(columns={
        "LocationID": "PULocationID",
        "Borough":    "pickup_borough",
        "Zone":       "pickup_zone",
        "service_zone": "pickup_service_zone",
    })
    do_zones = zones_df.rename(columns={
        "LocationID":   "DOLocationID",
        "Borough":      "dropoff_borough",
        "Zone":         "dropoff_zone",
        "service_zone": "dropoff_service_zone",
    })

    df = valid_df.copy()

    # Coerce LocationID columns to int (they come as float from some Parquet versions)
    for col in ("PULocationID", "DOLocationID"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Join pickup zone
    df = df.merge(
        pu_zones[["PULocationID", "pickup_borough", "pickup_zone", "pickup_service_zone"]],
        on="PULocationID",
        how="left"
    )
    # Join dropoff zone
    df = df.merge(
        do_zones[["DOLocationID", "dropoff_borough", "dropoff_zone", "dropoff_service_zone"]],
        on="DOLocationID",
        how="left"
    )

    # Mark unknown zones explicitly so they appear in KPIs, not silently as NaN
    df["pickup_borough"]  = df["pickup_borough"].fillna("UNKNOWN_ZONE")
    df["pickup_zone"]     = df["pickup_zone"].fillna("UNKNOWN_ZONE")
    df["dropoff_borough"] = df["dropoff_borough"].fillna("UNKNOWN_ZONE")
    df["dropoff_zone"]    = df["dropoff_zone"].fillna("UNKNOWN_ZONE")

    # Join vendor name
    vendors_df = vendors_df.rename(columns={"VendorID": "VendorID"})
    df = df.merge(vendors_df, on="VendorID", how="left")
    df["vendor_name"] = df["vendor_name"].fillna(f"UNKNOWN_VENDOR(id={df['VendorID']})")

    # Derived: pickup_hour for time-of-day analysis
    df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour

    # Derived: fare_per_mile (guard against zero distance)
    df["fare_per_mile"] = df["fare_amount"] / df["trip_distance"].replace(0, float("nan"))

    # Derived: total_revenue (fare + tip; tip is 0 for cash payments but not fabricated)
    df["total_revenue"] = df["fare_amount"].fillna(0) + df["tip_amount"].fillna(0)

    logger.info("[TRANSFORM] Enrichment complete. %d rows, %d columns.", len(df), len(df.columns))
    return df


# ── Metrics ────────────────────────────────────────────────────────────────────

def calculate_metrics(enriched_df: pd.DataFrame) -> dict:
    """
    Calculate all 5 business metrics.

    Returns a dict: metric_name → DataFrame with results.
    All metric DataFrames are also collected into a single flat CSV
    (metrics_report.csv) with a `metric` column for easy reading.
    """
    metrics = {}

    # M1 — Revenue per Zone (pickup_borough)
    m1 = (
        enriched_df
        .groupby("pickup_borough", observed=True)["total_revenue"]
        .agg(trip_count="count", total_revenue="sum", avg_revenue_per_trip="mean")
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    m1.insert(0, "metric", "M1_Revenue_per_Borough")
    metrics["M1_Revenue_per_Borough"] = m1
    logger.info("[METRICS] M1 computed — %d boroughs.", len(m1))

    # M2 — Avg Trip Duration by Pickup Hour
    m2 = (
        enriched_df
        .groupby("pickup_hour", observed=True)["duration_minutes"]
        .agg(trip_count="count", avg_duration_min="mean", median_duration_min="median")
        .reset_index()
        .sort_values("pickup_hour")
    )
    m2.insert(0, "metric", "M2_Avg_Duration_by_Hour")
    metrics["M2_Avg_Duration_by_Hour"] = m2
    logger.info("[METRICS] M2 computed — %d hour buckets.", len(m2))

    # M3 — Trip Count per Vendor
    m3 = (
        enriched_df
        .groupby("vendor_name", observed=True)
        .agg(
            trip_count=("VendorID", "count"),
            total_revenue=("total_revenue", "sum"),
            avg_fare=("fare_amount", "mean"),
        )
        .reset_index()
        .sort_values("trip_count", ascending=False)
    )
    m3.insert(0, "metric", "M3_Trip_Count_per_Vendor")
    metrics["M3_Trip_Count_per_Vendor"] = m3
    logger.info("[METRICS] M3 computed — %d vendors.", len(m3))

    # M4 — Speed Plausibility Rate
    total_trips = len(enriched_df)
    plausible = enriched_df[
        (enriched_df["avg_speed_mph"] >= MIN_SPEED_MPH) &
        (enriched_df["avg_speed_mph"] <= MAX_SPEED_MPH)
    ]
    implausible = total_trips - len(plausible)
    plausibility_rate = 100.0 * len(plausible) / total_trips if total_trips > 0 else 0.0

    m4 = pd.DataFrame([{
        "metric":             "M4_Speed_Plausibility_Rate",
        "total_trips":        total_trips,
        "plausible_trips":    len(plausible),
        "implausible_trips":  implausible,
        "plausibility_rate_pct": round(plausibility_rate, 2),
        "speed_range":        f"[{MIN_SPEED_MPH},{MAX_SPEED_MPH}] mph",
    }])
    metrics["M4_Speed_Plausibility_Rate"] = m4
    logger.info(
        "[METRICS] M4 computed — %.1f%% speed-plausible trips.",
        plausibility_rate
    )

    # M5 — Median Fare per Mile by Borough
    m5 = (
        enriched_df[enriched_df["fare_per_mile"].notna() & (enriched_df["fare_per_mile"] > 0)]
        .groupby("pickup_borough", observed=True)["fare_per_mile"]
        .agg(
            trip_count="count",
            median_fare_per_mile="median",
            mean_fare_per_mile="mean",
        )
        .reset_index()
        .sort_values("median_fare_per_mile", ascending=False)
    )
    m5.insert(0, "metric", "M5_Median_Fare_per_Mile_by_Borough")
    metrics["M5_Median_Fare_per_Mile_by_Borough"] = m5
    logger.info("[METRICS] M5 computed — %d boroughs.", len(m5))

    return metrics


def save_outputs(enriched_df: pd.DataFrame, metrics: dict) -> None:
    """
    Persist processed trip data and metrics report to disk.

    The processed Parquet file is the primary input for any downstream
    consumers (dashboards, further analysis).  The CSV metrics report is
    what the business stakeholder reviews.
    """
    # Processed trips
    enriched_df.to_parquet(PROCESSED_TRIPS, index=False)
    logger.info("[TRANSFORM] Processed trips saved to %s (%d rows).", PROCESSED_TRIPS, len(enriched_df))

    # Metrics report — concatenate all metric DataFrames into one flat CSV
    all_metrics = pd.concat(metrics.values(), ignore_index=True, sort=False)
    all_metrics.to_csv(METRICS_CSV, index=False)
    logger.info("[TRANSFORM] Metrics report saved to %s.", METRICS_CSV)


def print_metrics_summary(metrics: dict) -> None:
    """Print a human-readable summary of each metric to the console."""
    print("\n" + "=" * 70)
    print("  NYC TLC — MONTHLY METRICS REPORT (January 2024)")
    print("=" * 70)

    # M1
    m1 = metrics.get("M1_Revenue_per_Borough")
    if m1 is not None:
        print("\nM1 — REVENUE BY PICKUP BOROUGH")
        print(m1.to_string(index=False))

    # M2
    m2 = metrics.get("M2_Avg_Duration_by_Hour")
    if m2 is not None:
        print("\nM2 — AVG TRIP DURATION BY PICKUP HOUR (top 5 longest + shortest)")
        combined = pd.concat([m2.nlargest(5, "avg_duration_min"),
                              m2.nsmallest(5, "avg_duration_min")])
        print(combined.to_string(index=False))

    # M3
    m3 = metrics.get("M3_Trip_Count_per_Vendor")
    if m3 is not None:
        print("\nM3 — TRIP COUNT & REVENUE BY VENDOR")
        print(m3.to_string(index=False))

    # M4
    m4 = metrics.get("M4_Speed_Plausibility_Rate")
    if m4 is not None:
        print("\nM4 — SPEED PLAUSIBILITY RATE")
        print(m4.to_string(index=False))

    # M5
    m5 = metrics.get("M5_Median_Fare_per_Mile_by_Borough")
    if m5 is not None:
        print("\nM5 — MEDIAN FARE PER MILE BY BOROUGH")
        print(m5.to_string(index=False))

    print("\n" + "=" * 70 + "\n")
