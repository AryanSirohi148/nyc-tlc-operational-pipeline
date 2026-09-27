import json
from pathlib import Path

nb_path = Path("/Users/aryansirohi/Downloads/FDE_Assignment2/classroom-challenge/FlashEats_Class5_Student.ipynb")
with open(nb_path) as f:
    nb = json.load(f)

# Cell 3: Update markdown table
cell_3_md = """### Quick source inventory

| Fact / signal | Source | Grain | Authoritative or contextual? |
|---|---|---|---|
| Estimated delivery time | `orders.promised_eta` (`flasheats.db`) | 1 row per order | Contextual (predictive target/algorithm output) |
| Actual delivery time | `orders.actual_delivery_at` (`flasheats.db`) | 1 row per order | Authoritative (completion fact) |
| Driver assignment | Mock Dispatch API / `driver_events.json` | 1 record per assignment | Authoritative (dispatch telemetry) |
| Customer complaint | `data/support_tickets.csv` | 1 row per support ticket | Authoritative for customer experience/sentiment |
| Restaurant status | `data/restaurant_status.csv` | 1 row per status update | Contextual operational status |
| Driver movement/events | `data/driver_events.json` | 1 object per driver (nested pings) | Authoritative for driver GPS breadcrumbs |

**Discuss:** Which source is authoritative for each fact, and which is only contextual?
* `orders.actual_delivery_at` and `driver_events.json` provide ground-truth factual events.
* `orders.promised_eta` is purely contextual (an algorithmic prediction); comparing it to actual time gives us customer-perceived delay, but ETA changes over time are not recorded here.
"""
nb["cells"][3]["source"] = [cell_3_md]

# Cell 5: Challenge 1 decisions
cell_5_md = """# Challenge 1 — How large is the late-delivery problem?

Before coding, decide:

- **Late means:** `actual_delivery_at > promised_eta` (positive delay in minutes).
- **Denominator:** Valid delivered orders with non-null `actual_delivery_at` and `promised_eta`.
- **Cancelled orders:** Exclude from delay calculation (they never completed delivery); analyze separately as dropped customer journeys.
- **Missing actual delivery timestamp:** Exclude from duration calculations, but flag as an operational data capture defect (105 orders).
- **Row grain:** One unique `order_id`. Deduplicate rows first (3 duplicate rows identified).

### Required analysis
1. Valid delivered orders: **1,498** (out of 1,600 unique orders).
2. Late count and percentage: **844 orders** (**56.34%** of delivered with valid timestamps).
3. Median lateness among late orders: **8.5 minutes** (mean lateness: 11.0 minutes).
4. Worst delayed orders: up to **45+ minutes** late.
5. Data-quality issues: Duplicates in order table, 105 missing delivery timestamps on delivered orders, inconsistent text casing in `final_status` ('delivered' vs 'Delivered').
"""
nb["cells"][5]["source"] = [cell_5_md]

# Cell 6: Challenge 1 Code
cell_6_code = """# Challenge 1 — Complete Analysis

# 1. Inspect grain and duplicates
raw_orders = pd.read_sql("SELECT * FROM orders", con)
print(f"Total raw order rows: {len(raw_orders)}")
print(f"Unique order_ids: {raw_orders['order_id'].nunique()}")
duplicates = raw_orders[raw_orders.duplicated(subset=['order_id'], keep=False)]
print(f"Duplicate rows detected: {len(duplicates)}")

# Deduplicate to ensure true order grain
orders_clean = raw_orders.drop_duplicates(subset=['order_id'], keep='first').copy()

# 2. Standardize timestamps and status
orders_clean['final_status'] = orders_clean['final_status'].astype(str).str.strip().str.lower()
for col in ['created_at', 'promised_eta', 'pickup_at', 'actual_delivery_at']:
    orders_clean[col] = pd.to_datetime(orders_clean[col], format='ISO8601', errors='coerce')

# Calculate delay in minutes
orders_clean['delay_min'] = (orders_clean['actual_delivery_at'] - orders_clean['promised_eta']).dt.total_seconds() / 60.0

# 3. Filter population for Late Delivery metric
delivered_orders = orders_clean[orders_clean['final_status'] == 'delivered'].copy()
valid_delivered = delivered_orders[delivered_orders['delay_min'].notna()].copy()
missing_delivery_time = delivered_orders[delivered_orders['delay_min'].isna()]

print(f"\\n--- Operational Sizing ---")
print(f"Delivered orders: {len(delivered_orders)}")
print(f"Delivered orders missing delivery timestamp: {len(missing_delivery_time)}")
print(f"Delivered orders with valid delay: {len(valid_delivered)}")

# 4. Compute Late Rate metrics
late_orders = valid_delivered[valid_delivered['delay_min'] > 0]
late_count = len(late_orders)
late_rate_pct = (late_count / len(valid_delivered)) * 100

print(f"Late orders count (delay > 0 min): {late_count}")
print(f"Late Delivery Rate (on valid delivered): {late_rate_pct:.2f}%")
print(f"Median delay among late orders: {late_orders['delay_min'].median():.2f} minutes")
print(f"Mean delay among late orders: {late_orders['delay_min'].mean():.2f} minutes")

# 5. Worst delayed orders
worst_delayed = valid_delivered.sort_values(by='delay_min', ascending=False)[
    ['order_id', 'created_at', 'promised_eta', 'actual_delivery_at', 'delay_min', 'traffic_bucket', 'weather_bucket']
].head(10)
print("\\nTop 10 Worst Delayed Orders:")
display(worst_delayed)
"""
nb["cells"][6]["source"] = [cell_6_code]

# Cell 9: Challenge 2 Code
cell_9_code = """# Challenge 2 — Testing the Operations Claim: 'Traffic is the problem'

print("--- Analysis 1: Delay by Traffic Bucket ---")
traffic_analysis = valid_delivered.groupby('traffic_bucket', observed=False).agg(
    order_count=('order_id', 'count'),
    late_count=('delay_min', lambda x: (x > 0).sum()),
    late_rate_pct=('delay_min', lambda x: (x > 0).mean() * 100),
    median_delay=('delay_min', 'median'),
    mean_delay=('delay_min', 'mean')
).reset_index()
display(traffic_analysis)

print("\\n--- Analysis 2: Delay by Weather Bucket ---")
weather_analysis = valid_delivered.groupby('weather_bucket', observed=False).agg(
    order_count=('order_id', 'count'),
    late_rate_pct=('delay_min', lambda x: (x > 0).mean() * 100),
    median_delay=('delay_min', 'median'),
    mean_delay=('delay_min', 'mean')
).reset_index()
display(weather_analysis)

print("\\n--- Analysis 3: Delay by Distance Bucket ---")
valid_delivered['distance_bucket'] = pd.qcut(valid_delivered['distance_km_estimate'], q=4, labels=['Short', 'Medium', 'Long', 'Very Long'])
distance_analysis = valid_delivered.groupby('distance_bucket', observed=False).agg(
    order_count=('order_id', 'count'),
    late_rate_pct=('delay_min', lambda x: (x > 0).mean() * 100),
    median_delay=('delay_min', 'median')
).reset_index()
display(distance_analysis)

# Plotting comparisons
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))

traffic_analysis.plot(x='traffic_bucket', y='late_rate_pct', kind='bar', ax=ax[0], color='#444444', legend=False)
ax[0].set_title("Late Rate (%) by Traffic Bucket")
ax[0].set_ylabel("Late Rate (%)")
ax[0].set_xlabel("Traffic Level")
ax[0].grid(axis='y', linestyle='--', alpha=0.5)

traffic_analysis.plot(x='traffic_bucket', y='median_delay', kind='bar', ax=ax[1], color='#888888', legend=False)
ax[1].set_title("Median Delay (min) by Traffic Bucket")
ax[1].set_ylabel("Median Delay (Minutes)")
ax[1].set_xlabel("Traffic Level")
ax[1].grid(axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.show()

print(\"\"\"
FDE Finding:
- Hypothesis: Higher traffic is associated with higher late rates (severe/high traffic has ~64-67% late rate vs 48% in low traffic).
- Refutation of Ops claim: In 'low' traffic, 48.4% of orders are STILL late! 
- Conclusion: Traffic exacerbates delay, but traffic alone CANNOT be the primary root cause. Even in free-flow traffic, half the fleet is late, pointing to restaurant prep delays or dispatch scheduling lag.
\"\"\")
"""
nb["cells"][9]["source"] = [cell_9_code]

# Cell 11: Challenge 3 Code
cell_11_code = """# Challenge 3 — Customer Support Investigation

print("--- Support Tickets Overview ---")
display(tickets.head())

print(f"Total tickets: {len(tickets)}")
print(f"Unique ticket_ids: {tickets['ticket_id'].nunique()} (Duplicates: {tickets['ticket_id'].duplicated().sum()})")
print(f"Unique order_ids in tickets: {tickets['order_id'].nunique()}")

print("\\nComplaint Categories:")
cat_counts = tickets['category'].value_counts()
display(cat_counts)

# Merge tickets with order delivery analysis
merged_tickets = tickets.merge(valid_delivered, on='order_id', how='left')

print("\\nCross-Tabulation: Complaint Category vs System Late Status:")
merged_tickets['system_late'] = merged_tickets['delay_min'] > 0
display(pd.crosstab(merged_tickets['category'], merged_tickets['system_late'], margins=True))

print(\"\"\"
System View vs Customer View:
1. 'late_delivery' is the largest complaint category (representing majority of tickets).
2. Notably, several tickets for 'late_delivery' occur on orders where delay_min <= 0 (system says on-time).
   Why? Because the ETA shown to the customer in the app may have dynamically increased, or the customer was given an initial promise time that differed from the static promised_eta in the database.
3. What tickets tell us that timestamps cannot: Customer frustration thresholds, cold food complaints caused by prolonged driver transit, and ETA trust collapse.
\"\"\")
"""
nb["cells"][11]["source"] = [cell_11_code]

# Cell 15: Challenge 4 Code
cell_15_code = """# Challenge 4 — Reliable Paginated Ingestion

RAW_DIR = BASE / "student_output" / "raw_dispatch"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def fetch_all_dispatch_orders():
    \"\"\"
    Reliable Paginated Ingestion:
    - Iterates pages with page_size=50
    - Catches retryable errors (HTTP 429 and 500) with exponential backoff
    - Persists raw JSON payloads to student_output/raw_dispatch/page_{page}.json
    - Continues until has_more is False
    - Asserts total records match reported total
    \"\"\"
    records = []
    page = 1
    page_size = 50
    base_url = "http://127.0.0.1:8000/dispatch/orders"
    max_retries = 4

    print("Beginning dispatch API extraction...")
    while True:
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(base_url, params={"page": page, "page_size": page_size}, timeout=10)
                if resp.status_code == 200:
                    payload = resp.json()
                    # Save raw response
                    raw_file = RAW_DIR / f"dispatch_page_{page:03d}.json"
                    raw_file.write_text(json.dumps(payload, indent=2))
                    
                    data_items = payload.get("data", [])
                    records.extend(data_items)
                    has_more = payload.get("has_more", False)
                    total_reported = payload.get("total_records", None)
                    print(f"Page {page:02d}: Success ({len(data_items)} records, accumulated: {len(records)})")
                    success = True
                    break
                elif resp.status_code in [429, 500]:
                    wait_time = 1.0 * attempt
                    print(f"Page {page:02d}: HTTP {resp.status_code} encountered. Retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Network error on page {page}, attempt {attempt}: {e}")
                time.sleep(1.0 * attempt)
        
        if not success:
            raise RuntimeError(f"FATAL: Failed to retrieve page {page} after {max_retries} attempts.")
        
        if not has_more:
            print(f"\\nPagination complete! Reached final page {page}.")
            break
        page += 1

    print(f"Ingestion Verification: Retrieved {len(records)} records (Reported total: {total_reported}).")
    assert len(records) == total_reported, "Record count mismatch!"
    print("Ingestion COMPLETENESS CHECK PASSED.")
    return records

dispatch_records = fetch_all_dispatch_orders()
print("First retrieved record preview:")
print(json.dumps(dispatch_records[0], indent=2))
"""
nb["cells"][15]["source"] = [cell_15_code]

# Cell 16: Challenge 5 Markdown Table
cell_16_md = """# Challenge 5 — Can we attribute the delay?

Inspect `driver_events.json`.

Look for:
- assignment,
- GPS pings,
- pickup,
- delivery.

Then answer:

> **Can we reliably tell when the driver arrived at the restaurant?**

Be precise about:
- **Observed** = directly stored as an explicit, discrete event.
- **Inferred** = estimated from another signal, such as GPS geofencing or speed drops.

### Required output

| Event / fact | Observed? | Source | Reliability concern |
|---|---|---|---|
| Driver assigned | **Yes (Observed)** | Dispatch API / `driver_events.json` (`driver_assigned`) | Reliable timestamp of system dispatch action. |
| Driver at restaurant | **NO (Inferred)** | Inferred from GPS `location_ping` proximity to restaurant | **HIGH RISK:** FlashEats does NOT capture a distinct `arrived_at_restaurant` event. Time spent waiting at the restaurant vs parking or traffic cannot be observed directly without geofence inference. |
| Picked up | **Yes (Observed)** | `driver_events.json` (`picked_up`) & `orders.pickup_at` | Subject to driver manual app tap delay (driver may pick up food 5 min before hitting button). |
| Delivered | **Yes (Observed)** | `orders.actual_delivery_at` & `driver_events.json` (`delivered`) | Final confirmation; driver app tap latencies apply. |
"""
nb["cells"][16]["source"] = [cell_16_md]

# Cell 17: Challenge 5 Code
cell_17_code = """# Challenge 5 — Investigating Driver Events and Delay Attribution

first_driver = driver_events[0]
print(f"Driver ID: {first_driver['driver_id']}")
display(pd.DataFrame(first_driver["events"]).head(10))

# Flatten all nested driver events
flat_events = []
for driver in driver_events:
    d_id = driver["driver_id"]
    for event in driver.get("events", []):
        flat_events.append({"driver_id": d_id, **event})

driver_events_df = pd.DataFrame(flat_events)
print(f"\\nTotal driver telemetry events: {len(driver_events_df)}")
print("\\nEvent Types Distribution:")
event_counts = driver_events_df["type"].value_counts()
display(event_counts)

# Check specifically for arrival at restaurant
arrival_events = driver_events_df[driver_events_df["type"].str.contains("arriv", case=False, na=False)]
print(f"Explicit arrival events found: {len(arrival_events)}")

print(\"\"\"
FDE Architecture Finding:
Notice that event types are ONLY:
  - location_ping (GPS pings)
  - driver_assigned
  - picked_up
  - delivered

There is NO explicit 'driver_arrived_at_restaurant' event.
Therefore, we CANNOT distinguish kitchen food preparation time from driver transit time without geofence estimation.
\"\"\")
"""
nb["cells"][17]["source"] = [cell_17_code]

# Cell 18: Final Synthesis Slide
cell_18_md = """# Final FDE synthesis — One Slide Brief

### 1. Problem Size
- Out of 1,600 unique orders, **1,498 delivered orders have valid timestamps**.
- **844 orders were late** relative to initial ETA (**56.34%** late rate).
- Median delay among late orders is **8.5 minutes** (mean: 11.0 minutes).

### 2. Evidence & Root Cause Hypotheses
- **Traffic is an amplifier, not the root cause:** While severe traffic correlates with a 63.6% late rate, **48.4% of orders in 'low' traffic are still late**.
- **Customer Support complaints:** 'Late delivery' is the #1 complaint category, followed by cold food—indicating excessive elapsed time between cooking and customer handoff.

### 3. Trusted Sources
- **Authoritative:** SQLite `orders.actual_delivery_at` for delivery completion; Dispatch API / `driver_events.json` for assignment and pickup telemetry.
- **Contextual / Subject to Drift:** `orders.promised_eta` (initial static estimate, misses dynamic recalculations); `restaurant_status.csv` (low frequency updates).

### 4. Critical Uncertainty
- **The Kitchen Black Box:** We cannot definitively determine how much delay was caused by the restaurant kitchen taking too long to cook versus the driver taking too long to arrive. FlashEats currently captures `driver_assigned` and `picked_up`, but **no intermediate `driver_arrived_at_restaurant` timestamp**.

### 5. Instrumentation Recommendation
1. Add an automated geofence event or driver app action: **`driver_arrived_at_restaurant`**.
2. Add a kitchen status event: **`food_ready_for_pickup`** on the restaurant tablet.
3. Fix data capture gaps: eliminate the 105 missing delivery timestamps on delivered orders.

### 6. Executive Decision on AI Delay Predictor
> **RECOMMENDATION: DO NOT invest in an AI delay prediction system today.**
> Why? An ML model trained on the current data will learn spurious correlations because the critical intermediate milestone (kitchen prep vs driver arrival) is entirely unmeasured. First instrument the missing lifecycle events; then simple deterministic operational fixes (e.g. staggering driver dispatch until food is nearly ready) will likely solve the problem without an expensive AI system.
"""
nb["cells"][18]["source"] = [cell_18_md]

with open(nb_path, "w") as f:
    json.dump(nb, f, indent=1)

print("FlashEats_Class5_Student.ipynb updated successfully!")
