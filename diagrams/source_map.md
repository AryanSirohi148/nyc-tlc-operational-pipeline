# Source Map — NYC TLC Yellow Taxi Pipeline

## Business Question → Information → Source System Mapping

```
Business Question                     Required Information              Source System
─────────────────────────────────────────────────────────────────────────────────────
Which zones drive the most            fare_amount, tip_amount,          TLC Monthly Parquet
revenue?                              PULocationID, DOLocationID        (data.nyc.gov)
                                                │
                                                ▼
                                      Zone name, borough               TLC Zone Lookup CSV
                                      (join on LocationID)             (data.nyc.gov)

Are trip durations reasonable?        tpep_pickup_datetime,            TLC Monthly Parquet
                                      tpep_dropoff_datetime,
                                      trip_distance

Which vendors have data quality       VendorID, trip counts,           TLC Monthly Parquet
problems?                             null rates per vendor            + Vendor metadata CSV

What does each field mean?            Field definitions,               NYC Open Data SODA API
                                      expected ranges                  (metadata endpoint)
```

## Source Inventory

| Source ID | Name                              | Type    | URL / Path                                              | Grain        | Owner         | Update Cadence |
|-----------|-----------------------------------|---------|---------------------------------------------------------|--------------|---------------|----------------|
| S1        | TLC Yellow Trip Records Jan-2024  | Parquet | https://d37ci6vzurychx.cloudfront.net/trip-data/        | 1 row/trip   | TLC           | Monthly        |
| S2        | TLC Taxi Zone Lookup              | CSV     | https://d37ci6vzurychx.cloudfront.net/misc/             | 1 row/zone   | TLC           | Infrequent     |
| S3        | NYC Open Data Metadata API        | JSON/API| https://data.cityofnewyork.us/api/views/                | 1 obj/field  | NYC Open Data | On change      |
| S4        | Vendor Metadata                   | CSV     | data/raw/vendor_metadata.csv (embedded)                 | 1 row/vendor | TLC docs      | Rare           |

## Source Ownership & Access

- **S1, S2**: Publicly downloadable from TLC's CloudFront CDN. No auth required. Direct HTTP download.
- **S3**: NYC Open Data SODA API — no API key required for metadata reads, rate limit 1000 req/day unauthenticated.
- **S4**: Derived from TLC's official data dictionary PDF, embedded in this repo as a small lookup file.

## Important Gaps Identified

| Gap | Impact | Handling |
|-----|--------|----------|
| No actual route geometry (only origin/destination zones) | Speed calculation is approximate | Documented as Limitation; flagged in speed metric |
| Tip amounts for cash payments are systematically NULL | Underestimates total revenue for cash trips | Known issue; fare_amount used as minimum revenue; tip not included for cash |
| No trip-level driver or vehicle ID | Cannot distinguish driver behaviour from vehicle behaviour | Out of scope for this pipeline |
| Historical data only — no real-time feed | Pipeline produces trailing-month KPIs, not live | Acceptable for monthly reporting use case |
| LocationID 264 and 265 = "Unknown" in zone lookup | Some trips cannot be attributed to a borough | Included but flagged in output |

## Retrieval Modes Used

1. **HTTP file download** — Parquet (S1) and CSV (S2) pulled via `requests` and saved to `data/raw/`
2. **REST API call** — SODA metadata endpoint (S3) called with `requests.get()` to retrieve field definitions as JSON
3. **Local file read** — Vendor CSV (S4) read with `pandas.read_csv()` from the repo
```
