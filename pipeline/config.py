"""
config.py — Central configuration for the NYC TLC pipeline.

All paths, URLs, and thresholds live here so that changing them
does not require touching any other module.
"""

import os
from pathlib import Path

# ── Root paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW      = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUTS       = PROJECT_ROOT / "outputs"

# Make sure all directories exist when this module is imported
for _d in (DATA_RAW, DATA_PROCESSED, OUTPUTS):
    _d.mkdir(parents=True, exist_ok=True)

# ── Source URLs ───────────────────────────────────────────────────────────────
TLC_PARQUET_URL = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data/"
    "yellow_tripdata_2024-01.parquet"
)
TLC_ZONE_CSV_URL = (
    "https://d37ci6vzurychx.cloudfront.net/misc/taxi+_zone_lookup.csv"
)
# NYC Open Data SODA metadata endpoint (returns JSON — no API key needed)
SODA_METADATA_URL = (
    "https://data.cityofnewyork.us/api/views/biws-g3hs.json"
)

# ── Raw file paths ─────────────────────────────────────────────────────────────
RAW_PARQUET  = DATA_RAW / "yellow_tripdata_2024-01.parquet"
RAW_ZONES    = DATA_RAW / "taxi_zone_lookup.csv"
RAW_VENDORS  = DATA_RAW / "vendor_metadata.csv"
RAW_METADATA = DATA_RAW / "tlc_field_metadata.json"

# ── Processed file paths ───────────────────────────────────────────────────────
PROCESSED_TRIPS = DATA_PROCESSED / "validated_trips.parquet"

# ── Output file paths ──────────────────────────────────────────────────────────
METRICS_CSV    = OUTPUTS / "metrics_report.csv"
VALIDATION_CSV = OUTPUTS / "validation_log.csv"
PIPELINE_LOG   = OUTPUTS / "pipeline_run.log"

# ── Validation thresholds ──────────────────────────────────────────────────────
# Trip duration: must be between 1 minute and 5 hours
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 300

# Trip distance: must be between 0.1 miles and 200 miles
MIN_DISTANCE_MILES = 0.1
MAX_DISTANCE_MILES = 200.0

# Average speed: must be between 5 mph and 80 mph
MIN_SPEED_MPH = 5.0
MAX_SPEED_MPH = 80.0

# Passenger count: 1 to 6 (TLC max capacity)
MIN_PASSENGERS = 1
MAX_PASSENGERS = 6

# Fare: must be > 0 for a trip to count toward revenue KPI
MIN_FARE = 0.0

# Valid vendor IDs per TLC data dictionary
VALID_VENDOR_IDS = {1, 2}

# Valid payment types (1=Credit, 2=Cash, 3=No charge, 4=Dispute, 5=Unknown, 6=Voided)
VALID_PAYMENT_TYPES = {1, 2, 3, 4, 5, 6}

# ── Vendor metadata (embedded — from TLC data dictionary) ─────────────────────
VENDOR_METADATA = [
    {"VendorID": 1, "vendor_name": "Creative Mobile Technologies (CMT)"},
    {"VendorID": 2, "vendor_name": "VeriFone Inc."},
]

# ── Sampling ───────────────────────────────────────────────────────────────────
# Set to None to process all rows; set to an integer for a fast dev run
SAMPLE_ROWS = None   # e.g. 500_000 for a quick run on large files
