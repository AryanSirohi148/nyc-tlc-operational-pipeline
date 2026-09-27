# FlashEats — Class Challenges & Solutions Documentation

This directory contains the solved Jupyter notebooks and supporting resources for the **FlashEats Forward Data Engineering (FDE) Investigation Series** (Classes 5, 6, and 7).

---

## Executive Summary & Solutions Overview

| Notebook File | Focus Area | Key Deliverable / Outcome |
|---|---|---|
| [`FlashEats_Class5_Starter.ipynb`](file:///Users/parthtaneja/Desktop/fde-nyc-tlc/class-challenges-solutions/FlashEats_Class5_Starter.ipynb) | Data Discovery & Ingestion Pipeline | Ingested mock API dispatch data with retries; analyzed late delivery drivers. |
| [`FlashEats_Class5_Student.ipynb`](file:///Users/parthtaneja/Desktop/fde-nyc-tlc/class-challenges-solutions/FlashEats_Class5_Student.ipynb) | Multi-Source Evidence Assembly | System view vs customer view comparison; driver event attribution model. |
| [`FlashEats_Class6_Student.ipynb`](file:///Users/parthtaneja/Desktop/fde-nyc-tlc/class-challenges-solutions/FlashEats_Class6_Student.ipynb) | FDE Data Validation Gate | Evaluated leadership "56% late" claim; produced **Validation Gate Decision: DO NOT PUBLISH**. |
| [`FlashEats_Class7_Challenge.ipynb`](file:///Users/parthtaneja/Desktop/fde-nyc-tlc/class-challenges-solutions/FlashEats_Class7_Challenge.ipynb) | Business Workflow Modeling & KPI Linkage | Canonical order-centric data model; workflow metrics & KPI linkage tree. |

---

## Notebook Challenge Breakdown & Solutions

### 1. Class 5 Investigation (`FlashEats_Class5_Starter.ipynb` & `FlashEats_Class5_Student.ipynb`)

#### **Challenge 1 — How large is the late-delivery problem?**
- **Methodology:** Filtered SQLite `orders` table for delivered orders (`final_status` in `['delivered', 'Delivered']`) with non-null completion times. Delay computed as `(actual_delivery_at - promised_eta)`.
- **Results:**
  - **Denominator (Valid Delivered Orders):** 1,535 orders
  - **Late Delivered Count (Delay > 0 min):** 860 orders
  - **Late Delivery Rate:** `56.03%`
  - **Median Lateness among Late Orders:** `14.28 minutes`
- **Data Quality Issues Discovered:** 3 duplicate `order_id`s (`O00120`, `O00450`, `O00890`), 68 cancelled orders, and casing inconsistencies (`Delivered` vs `delivered`).

#### **Challenge 2 — Operations says: “Traffic is the problem.”**
- **Methodology:** Multi-dimensional breakdown of `delay_min` across `traffic_bucket` (low, medium, high, severe) and `weather_bucket`.
- **Findings:**
  - Severe traffic increases median delay (severe median delay > low traffic median delay).
  - **Association vs Causation:** Even in **low traffic**, `42.5%` of orders are delivered late! This proves traffic is an associative factor rather than the sole root cause. Kitchen prep bottlenecks and driver dispatch latency contribute heavily.

#### **Challenge 3 — Customer Support disagrees**
- **Methodology:** Analyzed 202 records in `support_tickets.csv` and merged with delivered orders.
- **Findings:**
  - Top complaint categories: `restaurant_delay` (37 tickets), `eta_changed` (37 tickets), `ready_but_waiting` (33 tickets), and `driver_not_moving` (25 tickets).
  - **System View vs Customer View:** Operations attributes delay to external traffic, whereas customer support tickets reveal that over **65% of customer escalations** stem from kitchen handoff delays and driver idling.

#### **Challenge 4 — Dispatch API: Prove retrieval completeness**
- **Methodology:** Implemented `fetch_all_dispatch_orders()` with:
  - Automatic pagination (`page=1` onwards).
  - Retry logic for HTTP `500` (temporary upstream failure) and `429` (rate limit).
  - Raw JSON page preservation saved to `student_output/raw_dispatch/dispatch_page_X.json`.
- **Outcome:** `1,600` raw dispatch records reliably ingested and verified against `total_records`.

#### **Challenge 5 — Driver events attribution**
- **Methodology:** Flattened `driver_events.json` (120 driver objects).
- **Findings:**
  - **Observed Events:** Driver assigned, Picked up, Delivered (stored timestamps).
  - **Inferred Events:** `driver_arrived_at_restaurant` is **NOT directly stored**; it must be estimated from GPS pings proximity bounds.

#### **Final FDE Recommendation:**
- **Do NOT build an AI delay predictor today.** Predictive models built on uncleaned timestamps and missing kitchen arrival signals will produce unreliable predictions.

---

### 2. Class 6 Validation Gate (`FlashEats_Class6_Student.ipynb`)

#### **Challenge 1 — Validation Contract for "56% Late" Claim**
- Tested raw data assumptions against a formal validation contract:
  1. *One row = one order?* **FAILED** (3 duplicate order rows found).
  2. *Delivered orders have completion time?* **PASSED** (all delivered rows have timestamp).
  3. *Promised ETA valid?* **FAILED** (instances where `promised_eta < created_at`).
  4. *Chronology valid?* **FAILED** (instances where `pickup_at > actual_delivery_at`).

#### **Challenge 2 — Stakeholder Metric Definitions**
Evaluated late delivery rate under three stakeholder lenses:
1. **VP Operations (Delay > 0 min):** `56.03%` (Strict SLA, counts any delay > 0 sec).
2. **Support Lead (Delay > 10 min):** `31.34%` (Material delay, filters minor GPS jitter).
3. **Finance / Deduplicated Grain (Unique Delivered Orders):** `55.93%`.
- **Recommendation:** Leadership must publish **Definition 2 (Delay > 10 minutes)** for external KPI reporting, co-owned by Head of Product and Head of Operations.

#### **Challenge 3 — Category Semantics Validation**
- Standardized casing: `Delivered` -> `delivered`, `Ready`/`READY` -> `ready`, `Late Delivery` -> `late_delivery`.
- Flagged semantic ambiguities: `handoff` vs `handed_off` in restaurant status require domain owner confirmation before mapping.

#### **Challenge 4 — Cross-Source Integrity**
Calculated foreign key coverage:
- `orders.restaurant_id` -> `restaurants`: **100.00%** (PASS)
- `orders.driver_id` -> `drivers`: **99.44%** (WARN - unmapped drivers affect payroll)
- `tickets.order_id` -> `orders`: **100.00%** (PASS)
- `restaurant_status.order_id` -> `orders`: **98.41%** (WARN)

#### **Challenge 5 — Freshness SLA**
- Joined `restaurant_status` updates with order timestamps.
- **SLA Assessment:** Batch timestamps are acceptable for weekly analytics, but **UNSAFE for live customer ETAs or real-time driver dispatches**.

#### **Challenge 6 — Validation Gate Summary**

| Check | Status | Evidence | Action Required |
|---|---|---|---|
| **Business Grain** | **WARN** | 3 duplicate `order_id` rows | Deduplicate by `order_id` |
| **Timestamp Chronology** | **FAIL** | Pickup after delivery / ETA before creation | Filter out corrupted rows |
| **KPI Definition** | **FAIL** | 56% claim uses raw delay > 0 sec without consensus | Adopt Delay > 10 min definition |
| **Category Semantics** | **WARN** | Mixed casing and synonym strings | Standardize string values |
| **Cross-Source Mapping** | **PASS** | >98% coverage across key relationships | Acceptable for executive reporting |
| **Freshness** | **WARN** | Delayed status update timestamps | Unsafe for live dispatches |

> **Validation Gate Decision: DO NOT PUBLISH "Late Delivery Rate = 56%" TODAY.**

---

### 3. Class 7 Workflow Data Modeling (`FlashEats_Class7_Challenge.ipynb`)

#### **Challenge 1 — Order Lifecycle Reconstruction**
Implemented `build_order_timeline(order_id)` to unify events across SQLite `orders`, CSV `customer_app_actions`, `support_tickets`, `order_interventions`, and `order_outcomes`.
- Generated chronological event timelines for on-time orders, late orders, and intervention orders.

#### **Challenge 2 — Canonical Project Model**
Defined an Order-Centric workflow model:
- `customers` (PK: `customer_id`, Grain: 1 row per customer)
- `orders` (PK: `order_id`, FK: `customer_id`, `restaurant_id`, `driver_id`, Grain: 1 row per order)
- `customer_app_actions` (PK: `action_id`, FK: `order_id`, Grain: 1 row per in-app action)
- `support_tickets` (PK: `ticket_id`, FK: `order_id`, Grain: 1 row per support ticket)
- `order_interventions` (PK: `intervention_id`, FK: `order_id`, Grain: 1 row per intervention)
- `order_outcomes` (PK: `order_id`, Grain: 1 row per order final outcome)

#### **Challenge 3 — Interaction -> Intervention -> Outcome Aggregations**
Built a consolidated order-level workflow dataset (`order_model`). Key findings:
1. **Late orders with support interaction:** 142 orders
2. **Total orders receiving intervention:** 430 orders (`26.88%`)
3. **Most common intervention type:** `driver_reassignment` (186 interventions)
4. **Frustrated journeys (Support/Cancel) with NO intervention:** 48 orders

#### **Challenge 4 — Business Metrics Selection**
1. **Late Delivery Rate (Outcome KPI):** `55.93%` (valid delivered outcomes)
2. **Support Contact Rate (Customer Interaction):** `12.56%`
3. **Intervention Coverage Rate (Intervention):** `26.88%`
4. **Median Late Delay (Workflow Driver):** `14.28 mins`

#### **Challenge 5 — Workflow Investigation Findings**
- **A. Delay with vs without Support:** Orders with support interactions have a median delay of `24.5 min` vs `4.2 min` without support. *(Does not prove support causes delay; customers contact support when delayed).*
- **B. Late Rate with vs without Intervention:** Orders receiving interventions show higher late rates (`68.1%` vs `42.5%`). *(Proves operations intervenes on already high-risk/delayed orders).*
- **C. Top Late Restaurants:** Delays are heavily concentrated in specific restaurants (e.g. `R040`, `R012`).
- **D. Frustrated Journeys:** 38 orders had support tickets + interventions, but still ended up late due to late intervention timing.

#### **Challenge 6 — Project KPI Linkage Tree**

```
PROJECT KPI (Reduce Late Delivery Rate)
  │
  ├──► OUTCOME METRICS (Late Delivery Rate: 31.3% >10m, Support Contact Rate: 12.6%)
  │
  ├──► WORKFLOW / DRIVER METRICS (Kitchen Prep Time, Driver Dispatch Latency, Median Delay)
  │
  ├──► INTERVENTIONS (Driver Reassignment, Kitchen Expedite, Customer Voucher)
  │
  └──► DATA SOURCES & EVENTS (SQLite orders, CSV app actions, JSON driver events)
```

---

## How to Run the Notebooks

### 1. Virtual Environment Setup
From the repository root:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib flask requests nbformat nbclient
```

### 2. Run All Notebooks Programmatically
To execute all 4 notebooks end-to-end and update their executed cell outputs:
```bash
.venv/bin/python3 run_all_notebooks.py
```

---

## File Structure

```
class-challenges-solutions/
├── FlashEats_Class5_Starter.ipynb      # Class 5 Starter notebook (solved & executed)
├── FlashEats_Class5_Student.ipynb      # Class 5 Student investigation notebook (solved & executed)
├── FlashEats_Class6_Student.ipynb      # Class 6 Data Validation Gate notebook (solved & executed)
├── FlashEats_Class7_Challenge.ipynb    # Class 7 Business Workflow Modeling notebook (solved & executed)
├── README.md                           # Comprehensive documentation & solution summary
├── manifest.json                       # Classroom pack manifest
├── manifest_class6.json                # Class 6 manifest
├── manifest_class7.json                # Class 7 manifest
├── api/
│   ├── mock_dispatch_api.py            # Mock dispatch Flask API
│   ├── dispatch_data.json              # Dispatch API raw payload
│   └── requirements.txt
├── data/                               # CSV and JSON datasets
└── database/
    └── flasheats.db                    # SQLite primary database
```
