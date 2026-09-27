# NYC Taxi Trip Operations — FDE Data Foundations Assignment 2

**Track B — NYC TLC (Taxi & Limousine Commission)**  
*From Client Data to a Dependable Pipeline*

---

## Problem Statement

The NYC Taxi & Limousine Commission (TLC) collects trip-level records across its licensed fleet but has no consolidated operational view of trip performance. Leadership wants to understand whether trip durations and fares are in line with expectations, which locations generate the most revenue, and how fleet utilization varies across time. Currently the data sits in separate monthly Parquet files (by vendor), an API endpoint for zone lookups, and a CSV lookup table for vendor metadata — none of which are joined or validated.

**Business question being answered:**  
*"Which pickup zones and time-of-day windows are driving the most revenue, and are there systematic quality or duration anomalies that should disqualify trips from any KPI calculation?"*

---

## Users / Stakeholders

| Role | Interest |
|---|---|
| TLC Operations Director | Monthly KPI dashboard — revenue per zone, avg trip duration |
| Fleet Analytics Team | Identify anomalous vendors or locations |
| Data Engineering Team | Reliable, repeatable pipeline they can schedule |
| Compliance Officer | Know exactly which trips were dropped and why |

---

## Project KPI

**Primary KPI:** Revenue per Zone per Month (fare_amount + tip_amount, restricted to validated trips only)

**Supporting KPIs:**
1. Average trip duration (minutes) by pickup hour — to detect operational anomalies
2. Trip count per vendor — to assess data completeness across suppliers
3. Speed-plausibility rate — % of trips with avg speed in [5, 80] mph
4. Fare-per-mile — median fare per mile, segmented by borough

---

## Source Overview

| Source | Type | Retrieval Mode | Grain | Owner |
|---|---|---|---|---|
| TLC Yellow Taxi Trip Records (Jan 2024) | Parquet file | HTTP download / file read | One row per trip | TLC / NYC Open Data |
| TLC Zone Lookup | CSV file | HTTP download / file read | One row per LocationID | TLC |
| TLC Data Dictionary | API / JSON | HTTP GET | One JSON object per field | data.cityofnewyork.us |
| Vendor metadata | Inline CSV (embedded) | File read | One row per VendorID | TLC documentation |

**At least two retrieval modes used:** HTTP file download (Parquet + CSV) and a SODA API call (NYC Open Data metadata endpoint).

---

## Repository Structure

```
FDE_Assignment2/
├── README.md                          <- this file
├── diagrams/
│   ├── source_map.md                  <- source map diagram
│   └── workflow_data_model.md         <- entity/event model diagram
├── data/
│   ├── raw/                           <- preserved raw inputs (never modified)
│   │   ├── yellow_tripdata_2024-01.parquet
│   │   ├── taxi_zone_lookup.csv
│   │   └── vendor_metadata.csv
│   └── processed/                     <- cleaned outputs
│       └── validated_trips.parquet
├── notebooks/
│   ├── 01_source_understanding.ipynb  <- Class 4: source map, grain, gaps
│   ├── 02_retrieval.ipynb             <- Class 5: retrieval + completeness checks
│   ├── 03_profiling_validation.ipynb  <- Class 6: profiling + validation rules
│   ├── 04_workflow_modelling.ipynb    <- Class 7: entity model + 5 metrics
│   └── 05_pipeline_walkthrough.ipynb  <- Class 8: pipeline trace + output
├── pipeline/
│   ├── pipeline.py                    <- runnable end-to-end pipeline script
│   ├── ingest.py                      <- retrieval module
│   ├── validate.py                    <- validation module
│   ├── transform.py                   <- modelling + metric calculation
│   └── config.py                      <- paths, thresholds, constants
└── outputs/
    ├── metrics_report.csv             <- final evidence table (5 metrics)
    ├── validation_log.csv             <- row-level rejection log
    └── pipeline_run.log               <- pipeline execution log
```

---

## Setup & Run Instructions

### Requirements

```bash
pip install pandas pyarrow requests duckdb rich tabulate matplotlib seaborn
```

### Run the full pipeline (one command)

```bash
cd FDE_Assignment2
python pipeline/pipeline.py
```

The pipeline will:
1. Download raw data if not already present in `data/raw/`
2. Validate all rows against business rules, writing rejects to `outputs/validation_log.csv`
3. Compute all 5 metrics and write them to `outputs/metrics_report.csv`
4. Log every step with timestamps to `outputs/pipeline_run.log`
5. Exit with code 0 on success, non-zero on any unrecoverable failure

### Re-run behaviour

The pipeline is **idempotent** — running it twice produces the same output. Processed files are overwritten, not appended.

---

## What Decision the Output Supports

The metrics report tells the TLC Operations Director which **pickup zones generate the highest validated revenue**, which **time windows have anomalous trip durations**, and which **vendors have data quality problems** (low speed-plausibility rates). This directly informs:
- Zone-level staffing and dispatch prioritisation
- Vendor compliance reviews
- Monthly KPI reporting to leadership

---

## Known / Unknown / Assumption / Limitation

| Category | Item |
|---|---|
| **Known** | TLC data has known duplicate trip IDs across vendors in some months |
| **Known** | Some LocationID values (e.g. 264, 265) are "Unknown" zones — trips from these are included but flagged |
| **Unknown** | Whether the Parquet file is the authoritative source or if a SQL database exists upstream |
| **Unknown** | Tip amounts for cash payments are not recorded — these are systematically missing, not random |
| **Assumption** | January 2024 is representative enough for a monthly pipeline demonstration |
| **Assumption** | VendorID 1 = Creative Mobile Technologies, VendorID 2 = VeriFone — sourced from TLC data dictionary |
| **Limitation** | Pipeline currently handles only Yellow Taxi data; Green Taxi and FHV would require additional schema mapping |
| **Limitation** | Speed calculation assumes straight-line distance from zone centroids, not actual route distance |

---

## FDE Judgement Call (for Demo)

**The most important judgement call:** Rather than silently dropping trips with zero or negative fare amounts (which is common in tutorials), I classified them into three buckets — `ZERO_FARE` (likely comp/test trips), `NEGATIVE_FARE` (likely correction entries), and `VALID` — and kept a rejection log. This matters because a business might legitimately want to count zero-fare trips as a customer-service metric, and silently removing them would make that impossible. The decision was documented as an assumption, not buried in code.
