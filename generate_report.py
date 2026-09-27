import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#333333"))
        
        # Running footer
        footer_text = "FDE Data Foundations — Assignment 2 Report  |  Roll No: 10283 (Aryan Sirohi)  |  Track B: NYC TLC"
        page_str = f"Page {self._pageNumber} of {page_count}"
        
        self.drawString(32, 20, footer_text)
        self.drawRightString(letter[0] - 32, 20, page_str)
        
        self.setStrokeColor(colors.HexColor("#777777"))
        self.setLineWidth(0.5)
        self.line(32, 29, letter[0] - 32, 29)
        self.restoreState()

def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=30,
        rightMargin=30,
        topMargin=25,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles - Academic, clean, human-written, black & white / grayscale
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12.2,
        leading=14,
        textColor=colors.black,
        spaceAfter=1
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.3,
        leading=10.3,
        textColor=colors.HexColor("#222222"),
        spaceAfter=3
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.0,
        leading=11.0,
        textColor=colors.black,
        spaceBefore=3.5,
        spaceAfter=2,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.6,
        leading=9.6,
        textColor=colors.HexColor("#111111"),
        spaceAfter=2.5
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.4,
        textColor=colors.HexColor("#111111"),
        leftIndent=9,
        spaceAfter=1.8
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.4,
        textColor=colors.black
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.0,
        leading=8.6,
        textColor=colors.black
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.7,
        leading=8.2,
        textColor=colors.black
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.7,
        leading=8.2,
        textColor=colors.black
    )

    table_cell_right = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.7,
        leading=8.2,
        alignment=2,
        textColor=colors.black
    )

    diag_title = ParagraphStyle(
        'DiagTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.2,
        textColor=colors.black,
        alignment=1
    )

    diag_text = ParagraphStyle(
        'DiagText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.4,
        leading=7.8,
        textColor=colors.HexColor("#222222"),
        alignment=1
    )

    diag_arrow = ParagraphStyle(
        'DiagArrow',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.0,
        leading=8.5,
        textColor=colors.HexColor("#444444"),
        alignment=1
    )

    story = []

    # ==================== PAGE 1 ====================
    # Title Block
    story.append(Paragraph("NYC TLC Operational Data Pipeline: Engineering Report", title_style))
    story.append(Paragraph("From Heterogeneous Raw Feeds to an Auditable, Dependable Ingestion & KPI Architecture", subtitle_style))
    
    meta_data = [[
        Paragraph("<b>Student:</b> Aryan Sirohi (Roll No: 10283)", table_cell_style),
        Paragraph("<b>Track:</b> Track B — NYC TLC Operations", table_cell_style),
        Paragraph("<b>Dataset:</b> Jan 2024 Yellow Taxi (2.96M trips)", table_cell_style),
        Paragraph("<b>Date:</b> September 2026", table_cell_style)
    ]]
    t_meta = Table(meta_data, colWidths=[150, 140, 160, 102])
    t_meta.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.black),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F6F6F6")),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 3))

    # Section 1: Problem Definition & Operational Context
    story.append(Paragraph("1. Problem Definition & Operational Context", h1_style))
    story.append(Paragraph(
        "The New York City Taxi & Limousine Commission (TLC) oversees yellow medallion taxi operations across the five boroughs. "
        "In January 2024 alone, over 2.96 million passenger trips were logged across separate in-vehicle vendor meters. However, fleet operations "
        "leadership lacked a consolidated, auditable view of fleet revenue realization, trip duration anomalies, and vendor reporting fidelity. "
        "Currently, raw trip records arrive partitioned by hardware vendor (Creative Mobile Technologies vs. VeriFone) in unvalidated Parquet files, "
        "taxi zone boundaries reside in a static CSV, and system metadata is exposed through an external municipal API.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The Operational Challenge:</b> Calculating core business metrics (e.g., revenue per zone, average trip duration, speed plausibility) "
        "directly on raw vendor records results in severe distortion due to zero-passenger test runs, uncalibrated GPS spikes (>100 mph), "
        "meter clock resets, and payment dispute reversals (negative fares). This project designs, validates, and executes an automated, "
        "idempotent data engineering pipeline that ingests multi-modal sources, applies 8 strict business validation rules, logs all dropped "
        "records into an auditable rejection ledger, and outputs dependable executive KPIs without silent data loss.",
        body_style
    ))

    # Section 2: Architecture & Data Flow Diagram (Built as clean structured nested boxes)
    story.append(Paragraph("2. System Architecture & End-to-End Data Flow", h1_style))
    
    # Layer 1: Sources (4 boxes side-by-side)
    layer1_cells = [
        [
            Paragraph("<b>TLC Trip Parquet</b><br/>Jan 2024 (2.96M trips)<br/>HTTP Stream / CDN", diag_text),
            Paragraph("<b>Zone Lookup CSV</b><br/>265 NYC Taxi Zones<br/>HTTP File Download", diag_text),
            Paragraph("<b>Vendor Metadata</b><br/>CMT & VeriFone Meta<br/>Local File Read", diag_text),
            Paragraph("<b>Data Dictionary</b><br/>SODA REST API<br/>JSON Metadata Endpoint", diag_text),
        ]
    ]
    t_layer1 = Table(layer1_cells, colWidths=[138, 138, 138, 138])
    t_layer1.setStyle(TableStyle([
        ('BOX', (0,0), (0,0), 0.5, colors.black),
        ('BOX', (1,0), (1,0), 0.5, colors.black),
        ('BOX', (2,0), (2,0), 0.5, colors.black),
        ('BOX', (3,0), (3,0), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F9F9F9")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Layer 2: Ingestion Box
    t_layer2 = Table([[
        Paragraph("<b>INGESTION & CONTRACT ENFORCEMENT (pipeline/ingest.py)</b><br/>"
                  "Schema type casting, UTC timestamp normalization, MD5/size caching, missing column boundary verification", diag_text)
    ]], colWidths=[552])
    t_layer2.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.75, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F2F2F2")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Layer 3: Validation Engine
    t_layer3 = Table([[
        Paragraph("<b>BUSINESS VALIDATION ENGINE (pipeline/validate.py)</b><br/>"
                  "Evaluates 8 Deterministic Rules (Duration [1,300m], Distance [0.1,200mi], Speed [5,80mph], Passenger [1,6], Fares)", diag_text)
    ]], colWidths=[552])
    t_layer3.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.75, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EAEAEA")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    # Layer 4: Two-branch Split
    t_layer4 = Table([
        [
            Paragraph("<b>AUDITABLE REJECTION LOG</b><br/><code>outputs/validation_log.csv</code><br/>"
                      "<b>415,151 rows (14.0%)</b><br/>Row-level failure codes (VR-01 to VR-07b)", diag_text),
            Paragraph("<b>DIMENSIONAL ENRICHMENT & MODELING</b><br/><code>data/processed/validated_trips.parquet</code><br/>"
                      "<b>2,549,473 rows (86.0%)</b> &mdash; Star schema join with Zones & Vendors", diag_text)
        ]
    ], colWidths=[271, 271])
    t_layer4.setStyle(TableStyle([
        ('BOX', (0,0), (0,0), 0.75, colors.black),
        ('BOX', (1,0), (1,0), 0.75, colors.black),
        ('BACKGROUND', (0,0), (0,0), colors.HexColor("#F7F7F7")),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor("#F0F0F0")),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))

    # Layer 5: Published KPIs
    t_layer5 = Table([[
        Paragraph("<b>PUBLISHED EXECUTIVE EVIDENCE REPORT (pipeline/transform.py -> outputs/metrics_report.csv)</b><br/>"
                  "M1: Revenue per Borough | M2: Hourly Trip Durations | M3: Vendor Share | M4: Speed Plausibility (100%) | M5: Median $/Mile", diag_text)
    ]], colWidths=[552])
    t_layer5.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.75, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E6E6E6")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))

    diag_assembly = [
        [t_layer1],
        [Paragraph("↓  HTTP Stream & Cached Download", diag_arrow)],
        [t_layer2],
        [Paragraph("↓  Validated Schema Ingestion", diag_arrow)],
        [t_layer3],
        [Paragraph("↓ 14.0% Rejections (Logged)                                                     ↓ 86.0% Validated Trips", diag_arrow)],
        [t_layer4],
        [Paragraph("↓  Aggregation & Metric Rollup Engine", diag_arrow)],
        [t_layer5]
    ]
    t_diagram_all = Table(diag_assembly, colWidths=[552])
    t_diagram_all.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 0.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0.5),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_diagram_all)
    story.append(Spacer(1, 2))

    # Section 3: Source System Inventory & Multi-Modal Retrieval
    story.append(Paragraph("3. Source System Inventory & Retrieval Modes", h1_style))
    story.append(Paragraph(
        "To satisfy multi-modal retrieval requirements without cross-system coupling, four distinct operational sources were integrated:",
        body_style
    ))
    
    src_data = [
        [Paragraph("Source Name", table_header_style),
         Paragraph("Format", table_header_style),
         Paragraph("Retrieval Mode", table_header_style),
         Paragraph("Grain", table_header_style),
         Paragraph("Owner / System", table_header_style),
         Paragraph("Identified Gaps & Operational Vulnerabilities", table_header_style)],
        
        [Paragraph("Yellow Trip Records", table_cell_bold),
         Paragraph("Parquet (Snappy)", table_cell_style),
         Paragraph("HTTP download (cached)", table_cell_style),
         Paragraph("1 row per completed trip", table_cell_style),
         Paragraph("TLC / CloudFront CDN", table_cell_style),
         Paragraph("Lacks referential constraints; unmetered trips present null passenger counts; negative fare entries.", table_cell_style)],
        
        [Paragraph("Taxi Zone Lookup", table_cell_bold),
         Paragraph("CSV", table_cell_style),
         Paragraph("HTTP download (cached)", table_cell_style),
         Paragraph("1 row per LocationID (1-265)", table_cell_style),
         Paragraph("NYC Open Data", table_cell_style),
         Paragraph("LocationIDs 264 & 265 map to 'Unknown' zone; borough polygons are coarse aggregations.", table_cell_style)],

        [Paragraph("Vendor Metadata", table_cell_bold),
         Paragraph("CSV (embedded)", table_cell_style),
         Paragraph("Local file read", table_cell_style),
         Paragraph("1 row per VendorID", table_cell_style),
         Paragraph("TLC Technical Specs", table_cell_style),
         Paragraph("Historical extracts contain undocumented VendorIDs (e.g. 6); mapped deterministically (1=CMT, 2=VeriFone).", table_cell_style)],

        [Paragraph("TLC Data Dictionary", table_cell_bold),
         Paragraph("JSON / SODA API", table_cell_style),
         Paragraph("REST HTTP GET", table_cell_style),
         Paragraph("1 record per schema attribute", table_cell_style),
         Paragraph("data.cityofnewyork.us", table_cell_style),
         Paragraph("External network dependency; unannounced field renames can silently break downstream ETL.", table_cell_style)]
    ]
    t_src = Table(src_data, colWidths=[90, 62, 85, 75, 80, 160])
    t_src.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#444444")),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EAEAEA")),
        ('TOPPADDING', (0,0), (-1,-1), 1.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_src)
    story.append(Spacer(1, 2))

    # Section 4: Pipeline Dependability & Idempotency
    story.append(Paragraph("4. Pipeline Dependability, Modularity & Failure Handling", h1_style))
    story.append(Paragraph(
        "The automated production pipeline is fully implemented in modular Python scripts located in <code>pipeline/</code>:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Modularity:</b> Strictly decoupled into <code>ingest.py</code> (retrieval & local disk caching), <code>validate.py</code> (8 named business rules), "
        "<code>transform.py</code> (star-schema joins & metric rollups), and <code>config.py</code> (system constants), orchestrated by <code>pipeline.py</code>.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Idempotency & Re-entrancy:</b> Running the pipeline repeatedly produces identical, deterministic results. Existing raw downloads are verified "
        "via file-size checks rather than re-downloaded, while processed artifacts are atomically overwritten rather than appended.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>Explicit Failure Recovery:</b> HTTP timeouts, malformed schemas, and unreadable files immediately raise explicit exceptions with "
        "non-zero process exit codes, logging exact timestamps and stack traces to <code>outputs/pipeline_run.log</code> without silent failure.",
        bullet_style
    ))

    # Guarantee clean PageBreak
    story.append(PageBreak())

    # ==================== PAGE 2 ====================
    # Running Top Header on Page 2
    story.append(Paragraph("NYC TLC Operational Data Pipeline: Engineering Report (Cont.)", title_style))
    meta_p2 = [[
        Paragraph("<b>Student:</b> Aryan Sirohi (Roll No: 10283)", table_cell_style),
        Paragraph("<b>Run ID:</b> 20260927T133721Z", table_cell_style),
        Paragraph("<b>Runtime:</b> 43.1 Seconds", table_cell_style),
        Paragraph("<b>Pipeline Status:</b> PASSED (Exit Code: 0)", table_cell_style)
    ]]
    t_meta_p2 = Table(meta_p2, colWidths=[160, 130, 110, 152])
    t_meta_p2.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.black),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F6F6F6")),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_meta_p2)
    story.append(Spacer(1, 3))

    # Section 5: Validation Rule Set & Rejection Breakdown
    story.append(Paragraph("5. Business Validation Rules & Empirical Rejection Ledger", h1_style))
    story.append(Paragraph(
        "In compliance with zero silent-loss data engineering standards, every incoming record was tested against 8 deterministic rules. "
        "From 2,964,624 raw records, <b>2,549,473 passed (86.0%)</b> and <b>415,151 failed (14.0%)</b>, logged to <code>outputs/validation_log.csv</code>:",
        body_style
    ))

    val_data = [
        [Paragraph("Rule ID", table_header_style),
         Paragraph("Rule Name", table_header_style),
         Paragraph("Condition / Boundary", table_header_style),
         Paragraph("Rejection Count", table_header_style),
         Paragraph("% of Rejects", table_header_style),
         Paragraph("Operational Rationale", table_header_style)],

        [Paragraph("VR-03", table_cell_bold), Paragraph("Speed Plausibility", table_cell_style), Paragraph("Speed ∈ [5.0, 80.0] mph", table_cell_style),
         Paragraph("239,209", table_cell_right), Paragraph("57.6%", table_cell_right), Paragraph("Removes extreme gridlock crawls (<5 mph) and corrupt GPS leaps (>80 mph).", table_cell_style)],

        [Paragraph("VR-05", table_cell_bold), Paragraph("Passenger Count", table_cell_style), Paragraph("Count ∈ [1, 6] (non-null)", table_cell_style),
         Paragraph("171,687", table_cell_right), Paragraph("41.4%", table_cell_right), Paragraph("Excludes driver personal runs, cargo moves, and null unmetered entries.", table_cell_style)],

        [Paragraph("VR-02", table_cell_bold), Paragraph("Trip Distance", table_cell_style), Paragraph("Distance ∈ [0.1, 200.0] mi", table_cell_style),
         Paragraph("69,770", table_cell_right), Paragraph("16.8%", table_cell_right), Paragraph("Eliminates zero-distance meter flips and multi-state out-of-boundary hauls.", table_cell_style)],

        [Paragraph("VR-04a", table_cell_bold), Paragraph("Negative Fare", table_cell_style), Paragraph("fare_amount < $0.00", table_cell_style),
         Paragraph("37,448", table_cell_right), Paragraph("9.0%", table_cell_right), Paragraph("Dispute reversals and chargebacks must not corrupt gross trip revenue.", table_cell_style)],

        [Paragraph("VR-01", table_cell_bold), Paragraph("Trip Duration", table_cell_style), Paragraph("Duration ∈ [1.0, 300.0] min", table_cell_style),
         Paragraph("36,935", table_cell_right), Paragraph("8.9%", table_cell_right), Paragraph("Discards immediate accidental cancelations (<1 min) and abandoned meters (>5 hrs).", table_cell_style)],

        [Paragraph("VR-04b", table_cell_bold), Paragraph("Zero Fare", table_cell_style), Paragraph("fare_amount == $0.00", table_cell_style),
         Paragraph("893", table_cell_right), Paragraph("0.2%", table_cell_right), Paragraph("Segregates complimentary/test runs to preserve unit fare distributions.", table_cell_style)],

        [Paragraph("VR-07", table_cell_bold), Paragraph("Timestamp Order", table_cell_style), Paragraph("dropoff_time > pickup_time", table_cell_style),
         Paragraph("870", table_cell_right), Paragraph("0.2%", table_cell_right), Paragraph("Rejects corrupt clock synchronizations where trip ends before it starts.", table_cell_style)],

        [Paragraph("VR-06", table_cell_bold), Paragraph("Vendor Integrity", table_cell_style), Paragraph("VendorID ∈ {1, 2}", table_cell_style),
         Paragraph("260", table_cell_right), Paragraph("0.1%", table_cell_right), Paragraph("Drops uncertified hardware feeds to prevent outer join null cascades.", table_cell_style)],

        [Paragraph("VR-07b", table_cell_bold), Paragraph("Temporal Scope", table_cell_style), Paragraph("Pickup Year == 2024", table_cell_style),
         Paragraph("15", table_cell_right), Paragraph("<0.01%", table_cell_right), Paragraph("Filters out uncalibrated legacy hardware emitting years 2008/2009.", table_cell_style)]
    ]
    t_val = Table(val_data, colWidths=[40, 85, 95, 65, 55, 212])
    t_val.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#444444")),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EAEAEA")),
        ('TOPPADDING', (0,0), (-1,-1), 1.6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.6),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_val)
    story.append(Paragraph("<font size='6.5' color='#444444'><i>* Note: Individual records can fail multiple rules simultaneously; hence rejection categories sum to >415,151 rows.</i></font>", body_style))

    # Section 6: FDE Judgement Call
    story.append(Paragraph("6. FDE Judgement Call: Structured Partitioning vs. Silent Dropping", h1_style))
    fde_call_text = (
        "<b>Architectural Decision:</b> Standard tutorials routinely drop invalid rows via <code>df[df.fare > 0]</code>. "
        "In an enterprise production setting, this silent elimination destroys regulatory audit trails. "
        "We partitioned non-positive fares into two distinct operational classes: <code>NEGATIVE_FARE</code> (37,448 dispute corrections) and "
        "<code>ZERO_FARE</code> (893 promotional/system rides). All 415,151 rejected records were written with specific failure reason codes "
        "to <code>outputs/validation_log.csv</code>. This guarantees full auditability for compliance regulators while ensuring downstream "
        "KPI calculations remain strictly unbiased."
    )
    t_callout = Table([[Paragraph(fde_call_text, callout_style)]], colWidths=[552])
    t_callout.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor("#333333")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8F8F8")),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_callout)
    story.append(Spacer(1, 2.5))

    # Section 7: Epistemic Matrix
    story.append(Paragraph("7. Epistemic Matrix: Distinguishing Facts, Assumptions & Unknowns", h1_style))
    matrix_data = [
        [Paragraph("Category", table_header_style),
         Paragraph("Item & Empirical Statement", table_header_style),
         Paragraph("Operational Implication & System Context", table_header_style)],

        [Paragraph("FACT", table_cell_bold),
         Paragraph("2,964,624 raw records processed; 2,549,473 passed (86.0%) and 415,151 rejected (14.0%).", table_cell_style),
         Paragraph("Verified deterministically from January 2024 Parquet download and execution logs.", table_cell_style)],

        [Paragraph("FACT", table_cell_bold),
         Paragraph("Cash payment trips (<code>payment_type=2</code>) record exactly $0.00 tip amount.", table_cell_style),
         Paragraph("Cash tips are received directly by drivers and are unrecorded by the meter hardware.", table_cell_style)],

        [Paragraph("FACT", table_cell_bold),
         Paragraph("Vendor 2 (VeriFone) logged 1,961,857 trips (77.0%); Vendor 1 (CMT) logged 587,616 trips (23.0%).", table_cell_style),
         Paragraph("Reflects major fleet market share concentration across technology vendors.", table_cell_style)],

        [Paragraph("ASSUMPTION", table_cell_bold),
         Paragraph("Speeds <5 mph or >80 mph reflect uncalibrated GPS or stationary meter drift, not valid trips.", table_cell_style),
         Paragraph("Ensures downstream duration and speed KPIs represent active vehicle transportation.", table_cell_style)],

        [Paragraph("ASSUMPTION", table_cell_bold),
         Paragraph("January 2024 operating patterns are sufficiently representative for monthly fleet baseline.", table_cell_style),
         Paragraph("Extreme winter weather events may suppress overall trip volume relative to summer periods.", table_cell_style)],

        [Paragraph("UNKNOWN", table_cell_bold),
         Paragraph("Whether CloudFront Parquet files are static immutable replicas or batch warehouse exports.", table_cell_style),
         Paragraph("Direct access to upstream transactional OLTP databases would permit streaming CDC ingestion.", table_cell_style)],

        [Paragraph("UNKNOWN", table_cell_bold),
         Paragraph("Actual street-level routing taken between pickup and dropoff zone centroids.", table_cell_style),
         Paragraph("Without raw GPS waypoint breadcrumbs, detour congestion cannot be separated from direct routes.", table_cell_style)]
    ]
    t_matrix = Table(matrix_data, colWidths=[65, 235, 252])
    t_matrix.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#444444")),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EAEAEA")),
        ('TOPPADDING', (0,0), (-1,-1), 1.6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.6),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_matrix)
    story.append(Spacer(1, 2.5))

    # Section 8: Key Empirical Findings & Decision Support
    story.append(Paragraph("8. Key Empirical Findings & Operational Decision Support", h1_style))
    story.append(Paragraph(
        "The pipeline produced 5 verified operational metrics (saved in <code>outputs/metrics_report.csv</code>) supporting concrete decisions:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>M1 (Borough Revenue Dynamics):</b> Manhattan accounts for 89.2% of trip volume (2,273,838 trips) generating $40.48M at an average of "
        "$17.80/trip. In contrast, Queens produces $15.39M across 247,780 trips at an average of $62.11/trip &mdash; heavily driven by flat-rate "
        "airport business trips connecting JFK and LaGuardia. Brooklyn logged 14,804 trips ($459K) and the Bronx logged 4,280 trips ($147K).",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>M2 (Hourly Congestion Patterns):</b> Trip volume peaks at 18:00 (183,317 trips, avg 14.4 min) and reaches its trough at 04:00 (12,489 trips). "
        "Average trip duration peaks earlier at 16:00 (17.07 min average) reflecting pre-rush gridlock before vehicles clear core business corridors.",
        bullet_style
    ))
    story.append(Paragraph(
        "• <b>M5 (Fare-per-Mile Economics):</b> Median fare-per-mile is highest in Manhattan ($7.28/mi) due to minimum flag drops and congestion surcharges "
        "spread over short hop distances, compared to Queens ($4.08/mi) and Brooklyn ($5.13/mi) where longer highway mileage amortizes base fees.",
        bullet_style
    ))
    story.append(Paragraph(
        "<b>Executive Operational Decision:</b> TLC leadership should deploy compliance officers to Queens airport staging facilities during the "
        "15:00&ndash;18:00 peak revenue window to regulate flat-rate adherence, while using Manhattan duration baselines to evaluate congestion pricing impacts.",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated PDF: {filename}")

if __name__ == "__main__":
    out_file = "/Users/aryansirohi/Downloads/FDE_Assignment2/10283_Aryan_Sirohi.pdf"
    build_pdf(out_file)
