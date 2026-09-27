# Workflow & Data Model Diagram — NYC TLC Yellow Taxi Pipeline

## Entity Model

```
┌──────────────────────────────────────────────────────────────────────┐
│                          ENTITIES                                    │
├──────────────┬───────────────────────┬───────────────────────────────┤
│   Vendor     │         Zone          │            Trip               │
│  ──────────  │       ────────        │          ────────             │
│  VendorID PK │  LocationID PK        │  (VendorID, pickup_dt) PK     │
│  vendor_name │  zone_name            │  VendorID FK -> Vendor        │
│              │  borough              │  PULocationID FK -> Zone      │
│              │  service_zone         │  DOLocationID FK -> Zone      │
│              │                       │  tpep_pickup_datetime         │
│              │                       │  tpep_dropoff_datetime        │
│              │                       │  passenger_count              │
│              │                       │  trip_distance                │
│              │                       │  fare_amount                  │
│              │                       │  tip_amount                   │
│              │                       │  total_amount                 │
│              │                       │  payment_type                 │
│              │                       │  RatecodeID                   │
└──────────────┴───────────────────────┴───────────────────────────────┘
```

## Event / State Model (Trip Lifecycle)

```
 [Trip Requested]
        │
        ▼
 [Pickup Recorded]  ──── tpep_pickup_datetime, PULocationID
        │
        ▼
 [Trip In Progress] ──── trip_distance accumulating
        │
        ▼
 [Dropoff Recorded] ──── tpep_dropoff_datetime, DOLocationID
        │
        ▼
 [Fare Calculated]  ──── fare_amount, extras, tolls, surcharges
        │
        ▼
 [Payment Processed]──── tip_amount, payment_type, total_amount
        │
        ▼
 [Record Written]   ──── Row enters TLC Parquet file (vendor's system)
        │
        ▼
 [Validation Gate]  ──── Business rules applied (see validation module)
       / \
      /   \
 VALID    REJECTED ──── Written to validation_log.csv with reason code
   │
   ▼
 [Metric Calculation] ── Aggregated into 5 KPIs
```

## Relational Model (SQL view)

```sql
-- Central fact table (one row per validated trip)
validated_trips (
    vendor_id          INTEGER,   -- FK to vendor
    pickup_datetime    TIMESTAMP, -- trip start event
    dropoff_datetime   TIMESTAMP, -- trip end event
    duration_minutes   FLOAT,     -- derived: (dropoff - pickup) in minutes
    pickup_location_id INTEGER,   -- FK to zone
    dropoff_location_id INTEGER,  -- FK to zone
    trip_distance      FLOAT,     -- miles, from meter
    fare_amount        FLOAT,
    tip_amount         FLOAT,
    total_amount       FLOAT,
    payment_type       INTEGER,
    avg_speed_mph      FLOAT,     -- derived: distance / duration_hours
    validation_status  TEXT       -- VALID / ZERO_FARE / NEGATIVE_FARE / etc.
)

-- Dimension: vendor
vendor_dim (
    vendor_id   INTEGER PRIMARY KEY,
    vendor_name TEXT
)

-- Dimension: zone
zone_dim (
    location_id  INTEGER PRIMARY KEY,
    zone_name    TEXT,
    borough      TEXT,
    service_zone TEXT
)
```

## Interactions / Interventions / Outcomes

| Interaction | What happens | Captured how |
|---|---|---|
| Pickup event | Driver accepts trip at a zone | PULocationID + pickup_datetime |
| Dropoff event | Trip ends at a zone | DOLocationID + dropoff_datetime |
| Payment | Passenger pays; tip recorded (or not for cash) | payment_type + tip_amount |
| Data quality intervention | Row fails validation rule | validation_status field + rejection log |
| Metric output | Aggregation of validated trips | metrics_report.csv |

## 5 Metrics Linked to KPI

| # | Metric | Formula | Business Link |
|---|--------|---------|---------------|
| M1 | Revenue per Zone | SUM(fare + tip) grouped by pickup borough | Primary KPI: zone-level revenue |
| M2 | Avg Trip Duration by Hour | AVG(duration_minutes) grouped by pickup_hour | Operational anomaly detection |
| M3 | Trip Count per Vendor | COUNT(*) grouped by vendor_name | Vendor data completeness |
| M4 | Speed Plausibility Rate | % trips where 5 <= avg_speed_mph <= 80 | Data trustworthiness measure |
| M5 | Median Fare per Mile | MEDIAN(fare_amount / trip_distance) by borough | Pricing consistency check |
```
