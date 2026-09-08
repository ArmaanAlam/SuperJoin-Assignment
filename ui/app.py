import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st
import json
import os
import pandas as pd

from src.models.database import (
    SessionLocal, PDFModel, ChunkModel, FactModel, RelationshipModel, init_db, engine, Base
)
from src.pipeline.pipeline_runner import PipelineRunner
from src.config import settings

# Page Configuration with Stitch TruthGraph Theme
st.set_page_config(
    page_title="Fact Knowledge Layer | TruthGraph Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-Density Stitch Design System CSS (TruthGraph Intelligence Engine)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Sora:wght@400;600;700;800&display=swap" rel="stylesheet">

<style>
    /* Root Stitch Theme Variables */
    :root {
        --bg-void: #06090e;
        --surface-1: #0b0f17;
        --surface-2: #111827;
        --surface-3: #1a2234;
        --primary-cyan: #00f0ff;
        --primary-sky: #38bdf8;
        --corroborate-emerald: #00ff9d;
        --corroborate-bg: rgba(0, 255, 157, 0.12);
        --contradict-crimson: #ff2e63;
        --contradict-bg: rgba(255, 46, 99, 0.14);
        --reconcile-amber: #fbbf24;
        --reconcile-bg: rgba(251, 191, 36, 0.12);
        --border-matrix: rgba(56, 189, 248, 0.16);
        --font-sora: 'Sora', sans-serif;
        --font-inter: 'Inter', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    html, body, [class*="css"] {
        font-family: var(--font-inter);
        color: #dfe2ee;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-sora) !important;
        letter-spacing: -0.02em;
    }

    /* HUD Metrics Banner */
    .hud-metric-card {
        background: var(--surface-1);
        border: 1px solid var(--border-matrix);
        border-radius: 4px;
        padding: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
        position: relative;
        overflow: hidden;
    }
    .hud-metric-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--primary-cyan), transparent);
    }
    .hud-metric-title {
        font-family: var(--font-mono);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #849495;
        margin-bottom: 6px;
    }
    .hud-metric-value {
        font-family: var(--font-mono);
        font-size: 1.85rem;
        font-weight: 700;
        color: #f8fafc;
    }

    /* Epistemic Badges */
    .badge-pill {
        font-family: var(--font-mono);
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 4px 10px;
        border-radius: 2px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-corroborate {
        background: var(--corroborate-bg);
        color: var(--corroborate-emerald);
        border: 1px solid var(--corroborate-emerald);
        box-shadow: 0 0 10px rgba(0, 255, 157, 0.2);
    }
    .badge-contradict {
        background: var(--contradict-bg);
        color: var(--contradict-crimson);
        border: 1px solid var(--contradict-crimson);
        box-shadow: 0 0 10px rgba(255, 46, 99, 0.2);
    }
    .badge-reconcilable {
        background: var(--reconcile-bg);
        color: var(--reconcile-amber);
        border: 1px solid var(--reconcile-amber);
        box-shadow: 0 0 10px rgba(251, 191, 36, 0.2);
    }
    .badge-telemetry {
        background: rgba(56, 189, 248, 0.1);
        color: var(--primary-sky);
        border: 1px solid var(--primary-sky);
        font-family: var(--font-mono);
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 2px;
    }

    /* Point-wise Forensic Cards */
    .forensic-card {
        background: var(--surface-1);
        border: 1px solid var(--border-matrix);
        border-radius: 4px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    }
    .forensic-quote-box {
        background: #080c14;
        border-left: 3px solid var(--primary-cyan);
        padding: 10px 14px;
        font-family: var(--font-mono);
        font-size: 0.84rem;
        color: #cde8f6;
        margin: 8px 0;
        border-radius: 0 4px 4px 0;
    }
    .point-list {
        list-style-type: none;
        padding-left: 0;
        margin: 6px 0;
    }
    .point-list li {
        position: relative;
        padding-left: 18px;
        margin-bottom: 5px;
        font-size: 0.88rem;
        line-height: 1.45;
        color: #dfe2ed;
    }
    .point-list li::before {
        content: "▪";
        position: absolute;
        left: 2px;
        color: var(--primary-cyan);
        font-size: 0.95rem;
    }

    .reasoning-panel {
        background: #090e18;
        border: 1px solid #1e2c42;
        padding: 12px 16px;
        border-radius: 4px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB & Pipeline
init_db()
db = SessionLocal()
pipeline = PipelineRunner()

def get_stats():
    pdfs_count = db.query(PDFModel).count()
    facts_count = db.query(FactModel).count()
    corrob_count = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "CORROBORATE").count()
    contra_count = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "CONTRADICT").count()
    recon_count = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "RECONCILABLE").count()
    return pdfs_count, facts_count, corrob_count, contra_count, recon_count

# Sidebar Operational Console
with st.sidebar:
    st.markdown("### ⚡ TRUTHGRAPH HUD")
    st.caption("Forensic Epistemic Knowledge Layer")
    st.divider()

    st.markdown("#### 📄 Ingest Document")
    uploaded_file = st.file_uploader("Upload PDF Document", type=["pdf"])
    if uploaded_file is not None:
        if st.button("🚀 Process & Ingest PDF", use_container_width=True, type="primary"):
            save_path = settings.UPLOAD_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner(f"Parsing, chunking & extracting grounded facts from {uploaded_file.name}..."):
                try:
                    res = pipeline.process_pdf(str(save_path), filename=uploaded_file.name, db=db)
                    st.success(f"Ingested {res['facts_count']} facts | Discovered {res['relationships_count']} cross-doc relations")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ingestion error: {e}")

    st.divider()
    st.markdown("#### 🧪 Test Suites & Demos")
    if st.button("📥 Load 3 Demo PDFs + Failure Case", use_container_width=True):
        from scripts.create_demo_pdfs import create_all_demo_pdfs
        with st.spinner("Generating sample PDFs & running knowledge pipeline..."):
            pdf_paths = create_all_demo_pdfs()
            for path in pdf_paths:
                pipeline.process_pdf(str(path), filename=Path(path).name, db=db)
            st.success("All 4 evaluation PDFs loaded and reasoned!")
            st.rerun()

    if st.button("🗑️ Reset Database", use_container_width=True):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        st.info("Database reset.")
        st.rerun()

    st.divider()
    st.markdown("**System Telemetry:**")
    st.markdown(f"- **Provider:** `{settings.LLM_PROVIDER}`")
    st.markdown(f"- **Model:** `{settings.LLM_MODEL_NAME}`")
    st.markdown(f"- **Embedding:** `MiniLM-L6-v2 (384-dim)`")
    st.markdown(f"- **Grounding:** `Strict Char-Span Verification`")

# Main Content
n_pdfs, n_facts, n_corrob, n_contra, n_recon = get_stats()

# Header
st.title("⚡ Fact Knowledge Layer")
st.caption("Cross-document fact extraction, strict character grounding & cross-document relationship reasoning")

# HUD Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"""
    <div class="hud-metric-card">
        <div class="hud-metric-title">📁 Ingested Corpus</div>
        <div class="hud-metric-value">{n_pdfs}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="hud-metric-card">
        <div class="hud-metric-title">📌 Grounded Facts</div>
        <div class="hud-metric-value">{n_facts}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="hud-metric-card">
        <div class="hud-metric-title">🤝 Corroborations</div>
        <div class="hud-metric-value" style="color: var(--corroborate-emerald);">{n_corrob}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="hud-metric-card">
        <div class="hud-metric-title">⚡ Contradictions</div>
        <div class="hud-metric-value" style="color: var(--contradict-crimson);">{n_contra}</div>
    </div>
    """, unsafe_allow_html=True)
with col5:
    st.markdown(f"""
    <div class="hud-metric-card">
        <div class="hud-metric-title">🧩 Reconcilables</div>
        <div class="hud-metric-value" style="color: var(--reconcile-amber);">{n_recon}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Navigation Tabs
tab_showcase, tab_facts, tab_relationships, tab_comparator = st.tabs([
    "🎯 4 Demonstrated Cases",
    "📋 Grounded Facts Matrix",
    "🔗 Cross-Document Relations",
    "🔍 Interactive Fact Comparator"
])

# TAB 1: 4 Core Cases Showcase (Point-wise Presentation)
with tab_showcase:
    st.subheader("Target Evaluation Cases (Point-wise Analysis)")
    
    case1, case2, case3, case4 = st.tabs([
        "Case 1: Corroboration",
        "Case 2: Contradiction",
        "Case 3: Reconcilable through Context",
        "Case 4: Documented Failure Case"
    ])

    with case1:
        st.markdown("#### Case 1: Cross-Document Corroboration")
        corrobs = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "CORROBORATE").all()
        if corrobs:
            for r in corrobs:
                f1 = db.query(FactModel).filter(FactModel.fact_id == r.fact1_id).first()
                f2 = db.query(FactModel).filter(FactModel.fact_id == r.fact2_id).first()
                pdf1 = db.query(PDFModel).filter(PDFModel.pdf_id == f1.pdf_id).first() if f1 else None
                pdf2 = db.query(PDFModel).filter(PDFModel.pdf_id == f2.pdf_id).first() if f2 else None

                st.markdown(f"""
                <div class="forensic-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span class="badge-pill badge-corroborate">✓ CORROBORATE</span>
                        <span class="badge-telemetry">CONFIDENCE: {r.confidence * 100:.1f}%</span>
                    </div>
                    <ul class="point-list">
                        <li><strong>Source Document A:</strong> <code>{pdf1.filename if pdf1 else 'Doc 1'}</code> (Page {f1.page_number if f1 else '?'})</li>
                        <li><strong>Claim A:</strong> {f1.subject} — {f1.predicate}: <strong>{f1.value}</strong></li>
                        <div class="forensic-quote-box">Quote: "{f1.source_text}" [Span: {f1.char_start}:{f1.char_end}]</div>
                        <li><strong>Source Document B:</strong> <code>{pdf2.filename if pdf2 else 'Doc 2'}</code> (Page {f2.page_number if f2 else '?'})</li>
                        <li><strong>Claim B:</strong> {f2.subject} — {f2.predicate}: <strong>{f2.value}</strong></li>
                        <div class="forensic-quote-box">Quote: "{f2.source_text}" [Span: {f2.char_start}:{f2.char_end}]</div>
                    </ul>
                    <div class="reasoning-panel">
                        <strong style="color: var(--primary-cyan);">Reasoning Synthesis:</strong>
                        <ul class="point-list">
                            <li>{r.reasoning}</li>
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Click 'Load 3 Demo PDFs' in sidebar to inspect corroboration points.")

    with case2:
        st.markdown("#### Case 2: Genuine Contradiction")
        contras = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "CONTRADICT").all()
        if contras:
            for r in contras:
                f1 = db.query(FactModel).filter(FactModel.fact_id == r.fact1_id).first()
                f2 = db.query(FactModel).filter(FactModel.fact_id == r.fact2_id).first()
                pdf1 = db.query(PDFModel).filter(PDFModel.pdf_id == f1.pdf_id).first() if f1 else None
                pdf2 = db.query(PDFModel).filter(PDFModel.pdf_id == f2.pdf_id).first() if f2 else None

                st.markdown(f"""
                <div class="forensic-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span class="badge-pill badge-contradict">⚠ CONTRADICT</span>
                        <span class="badge-telemetry">CONFIDENCE: {r.confidence * 100:.1f}%</span>
                    </div>
                    <ul class="point-list">
                        <li><strong>Source Document A:</strong> <code>{pdf1.filename if pdf1 else 'Doc 1'}</code> (Page {f1.page_number if f1 else '?'})</li>
                        <li><strong>Claim A:</strong> {f1.subject} — {f1.predicate}: <strong style="color: #ff809b;">{f1.value}</strong></li>
                        <div class="forensic-quote-box">Quote: "{f1.source_text}"</div>
                        <li><strong>Source Document B:</strong> <code>{pdf2.filename if pdf2 else 'Doc 2'}</code> (Page {f2.page_number if f2 else '?'})</li>
                        <li><strong>Claim B:</strong> {f2.subject} — {f2.predicate}: <strong style="color: #ff809b;">{f2.value}</strong></li>
                        <div class="forensic-quote-box">Quote: "{f2.source_text}"</div>
                    </ul>
                    <div class="reasoning-panel">
                        <strong style="color: var(--contradict-crimson);">Contradiction Analysis:</strong>
                        <ul class="point-list">
                            <li>{r.reasoning}</li>
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Click 'Load 3 Demo PDFs' in sidebar to inspect contradiction points.")

    with case3:
        st.markdown("#### Case 3: Reconcilable through Context")
        recons = db.query(RelationshipModel).filter(RelationshipModel.relationship_type == "RECONCILABLE").all()
        if recons:
            for r in recons:
                f1 = db.query(FactModel).filter(FactModel.fact_id == r.fact1_id).first()
                f2 = db.query(FactModel).filter(FactModel.fact_id == r.fact2_id).first()
                pdf1 = db.query(PDFModel).filter(PDFModel.pdf_id == f1.pdf_id).first() if f1 else None
                pdf2 = db.query(PDFModel).filter(PDFModel.pdf_id == f2.pdf_id).first() if f2 else None

                st.markdown(f"""
                <div class="forensic-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span class="badge-pill badge-reconcilable">🧩 RECONCILABLE</span>
                        <span class="badge-telemetry">BASIS: {r.reconciliation_basis or 'Contextual'}</span>
                    </div>
                    <ul class="point-list">
                        <li><strong>Claim 1:</strong> {f1.subject} | {f1.predicate} = <strong>{f1.value}</strong> [Time: <code>{f1.time_scope or 'N/A'}</code> | Doc: <code>{pdf1.filename if pdf1 else 'Doc 1'}</code>]</li>
                        <li><strong>Claim 2:</strong> {f2.subject} | {f2.predicate} = <strong>{f2.value}</strong> [Time: <code>{f2.time_scope or 'N/A'}</code> | Doc: <code>{pdf2.filename if pdf2 else 'Doc 2'}</code>]</li>
                    </ul>
                    <div class="reasoning-panel">
                        <strong style="color: var(--reconcile-amber);">Reconciliation Breakdown:</strong>
                        <ul class="point-list">
                            <li>{r.reasoning}</li>
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Click 'Load 3 Demo PDFs' in sidebar to inspect reconcilable points.")

    with case4:
        st.markdown("#### Case 4: Documented Failure Case (Unit Normalization)")
        st.markdown("""
        <div class="forensic-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span class="badge-pill badge-contradict">⚠ INTENTIONAL FAILURE CASE</span>
                <span class="badge-telemetry">TYPE: Unit Parsing Mismatch</span>
            </div>
            <ul class="point-list">
                <li><strong>Premise 1:</strong> <code>Revenue was $5M</code> in Company A Annual Report 2024.</li>
                <li><strong>Premise 2:</strong> <code>Revenue: 5000 thousand USD</code> in Addendum statutory filing.</li>
                <li><strong>Current System Output:</strong> Flags as <code>CONTRADICT</code> instead of <code>RECONCILABLE</code> / <code>CORROBORATE</code>.</li>
                <li><strong>Root Cause:</strong> The dynamic extractor parsed <code>5000 thousand USD</code> as a literal string with unit <code>thousand USD</code> rather than converting 5000 × 1000 to standard numeric <code>$5,000,000</code>.</li>
                <li><strong>Engineering Fix:</strong> Add an explicit <strong>Unit Canonicalization Pre-processor</strong> (e.g. Pint / ISO currency normalizer) before cross-fact comparison.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# TAB 2: Grounded Facts Matrix (Point-wise Breakdown)
with tab_facts:
    st.subheader("Grounded Facts Matrix")

    f_col1, f_col2, f_col3 = st.columns(3)
    all_pdfs = db.query(PDFModel).all()
    pdf_filter = f_col1.selectbox("Filter by PDF", ["All"] + [p.filename for p in all_pdfs])
    all_types = list(set([f.fact_type for f in db.query(FactModel).all()]))
    type_filter = f_col2.selectbox("Filter by Fact Type", ["All"] + all_types)
    conf_filter = f_col3.slider("Minimum Extraction Confidence", 0.0, 1.0, 0.0, 0.05)

    query = db.query(FactModel)
    if pdf_filter != "All":
        target_pdf = db.query(PDFModel).filter(PDFModel.filename == pdf_filter).first()
        if target_pdf:
            query = query.filter(FactModel.pdf_id == target_pdf.pdf_id)
    if type_filter != "All":
        query = query.filter(FactModel.fact_type == type_filter)
    query = query.filter(FactModel.confidence >= conf_filter)

    facts = query.all()
    st.caption(f"Displaying **{len(facts)}** verified grounded facts:")

    for fact in facts:
        pdf_rec = db.query(PDFModel).filter(PDFModel.pdf_id == fact.pdf_id).first()
        doc_name = pdf_rec.filename if pdf_rec else "Unknown"

        with st.expander(f"📌 [{fact.fact_type.upper()}] {fact.subject} ➔ {fact.predicate}: {fact.value}"):
            st.markdown(f"""
            <ul class="point-list">
                <li><strong>Document Name:</strong> <code>{doc_name}</code></li>
                <li><strong>Page Index:</strong> Page {fact.page_number}</li>
                <li><strong>Subject Entity:</strong> <code>{fact.subject}</code></li>
                <li><strong>Predicate Action:</strong> <code>{fact.predicate}</code></li>
                <li><strong>Claimed Value:</strong> <strong style="color: var(--primary-cyan);">{fact.value}</strong></li>
                <li><strong>Measurement Unit:</strong> <code>{fact.unit or 'None'}</code></li>
                <li><strong>Temporal Scope:</strong> <code>{fact.time_scope or 'Unspecified'}</code></li>
                <li><strong>Model Confidence:</strong> <code>{fact.confidence * 100:.1f}%</code></li>
                <li><strong>Verbatim Source Grounding Quote:</strong></li>
                <div class="forensic-quote-box">"{fact.source_text}"</div>
                <li><strong>Character Offset Span in Chunk:</strong> <code>[{fact.char_start} : {fact.char_end}]</code></li>
                <li><strong>Chunk Provenance ID:</strong> <code>{fact.chunk_id}</code></li>
            </ul>
            """, unsafe_allow_html=True)

# TAB 3: Cross-Document Relations (Point-wise Format)
with tab_relationships:
    st.subheader("Cross-Document Relationship Matrix")

    r_type = st.radio(
        "Filter by Epistemic Relationship:",
        ["All", "CORROBORATE", "CONTRADICT", "RECONCILABLE"],
        horizontal=True
    )

    r_query = db.query(RelationshipModel)
    if r_type != "All":
        r_query = r_query.filter(RelationshipModel.relationship_type == r_type)

    rels = r_query.all()
    st.caption(f"Discovered **{len(rels)}** cross-document relationships:")

    for r in rels:
        f1 = db.query(FactModel).filter(FactModel.fact_id == r.fact1_id).first()
        f2 = db.query(FactModel).filter(FactModel.fact_id == r.fact2_id).first()
        if not f1 or not f2:
            continue

        pdf1 = db.query(PDFModel).filter(PDFModel.pdf_id == f1.pdf_id).first()
        pdf2 = db.query(PDFModel).filter(PDFModel.pdf_id == f2.pdf_id).first()

        badge_class = "badge-corroborate" if r.relationship_type == "CORROBORATE" else ("badge-contradict" if r.relationship_type == "CONTRADICT" else "badge-reconcilable")

        st.markdown(f"""
        <div class="forensic-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <span class="badge-pill {badge_class}">{r.relationship_type}</span>
                <span class="badge-telemetry">CONFIDENCE: {r.confidence * 100:.1f}%</span>
            </div>
            <ul class="point-list">
                <li><strong>Fact A ({pdf1.filename if pdf1 else 'Doc 1'}, Page {f1.page_number}):</strong> {f1.subject} — {f1.predicate}: <strong style="color:var(--primary-cyan);">{f1.value}</strong></li>
                <div class="forensic-quote-box">Quote: "{f1.source_text}"</div>
                <li><strong>Fact B ({pdf2.filename if pdf2 else 'Doc 2'}, Page {f2.page_number}):</strong> {f2.subject} — {f2.predicate}: <strong style="color:var(--primary-cyan);">{f2.value}</strong></li>
                <div class="forensic-quote-box">Quote: "{f2.source_text}"</div>
            </ul>
            <div class="reasoning-panel">
                <strong style="color: var(--primary-sky);">Reasoning Synthesis:</strong>
                <ul class="point-list">
                    <li>{r.reasoning}</li>
                    {f"<li><strong>Reconciliation Basis:</strong> <code>{r.reconciliation_basis}</code></li>" if r.reconciliation_basis else ""}
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

# TAB 4: Interactive Fact Comparator (Point-wise Live Analysis)
with tab_comparator:
    st.subheader("Interactive Point-wise Fact Comparator")
    st.markdown("Select any two extracted facts to evaluate cross-document alignment in real-time.")

    all_facts_list = db.query(FactModel).all()
    if len(all_facts_list) >= 2:
        options = {f"{f.fact_id} | {f.subject} - {f.predicate}: {f.value}": f for f in all_facts_list}
        
        c_left, c_right = st.columns(2)
        fact1_choice = c_left.selectbox("Select Fact 1", list(options.keys()), index=0)
        fact2_choice = c_right.selectbox("Select Fact 2", list(options.keys()), index=min(1, len(options) - 1))

        if st.button("⚡ Evaluate Relationship with Reasoner", type="primary"):
            f1_obj = options[fact1_choice]
            f2_obj = options[fact2_choice]
            
            f1_schema = Fact(**f1_obj.to_dict())
            f2_schema = Fact(**f2_obj.to_dict())

            with st.spinner("Executing semantic reasoning..."):
                rel_eval = pipeline.relationship_engine.classify_relationship(f1_schema, f2_schema)
                badge_class = "badge-corroborate" if rel_eval.relationship_type == "CORROBORATE" else ("badge-contradict" if rel_eval.relationship_type == "CONTRADICT" else "badge-reconcilable")

                st.markdown(f"""
                <div class="forensic-card" style="margin-top:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span class="badge-pill {badge_class}">{rel_eval.relationship_type.value}</span>
                        <span class="badge-telemetry">CONFIDENCE: {rel_eval.confidence * 100:.1f}%</span>
                    </div>
                    <ul class="point-list">
                        <li><strong>Fact 1 Evaluation:</strong> {f1_schema.subject} | {f1_schema.predicate} = <code>{f1_schema.value}</code></li>
                        <li><strong>Fact 2 Evaluation:</strong> {f2_schema.subject} | {f2_schema.predicate} = <code>{f2_schema.value}</code></li>
                        <li><strong>Reasoning Synthesis:</strong> {rel_eval.reasoning}</li>
                        {f"<li><strong>Reconciliation Basis:</strong> <code>{rel_eval.reconciliation_basis}</code></li>" if rel_eval.reconciliation_basis else ""}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Load or ingest at least 2 facts to use the comparator.")

db.close()
