import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "SUPERJOIN FACT KNOWLEDGE LAYER — ARCHITECTURAL SPECIFICATION")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.75)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
            
        # Footer
        self.setFont("Helvetica", 8)
        self.drawString(54, 36, "Superjoin Engineering Hiring Assignment | Production-Grade Architecture")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_str)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(54, 46, 8.5 * inch - 54, 46)
        
        self.restoreState()

def build_pdf(filename="Fact_Knowledge_Layer_Documentation.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#0f172a") # Slate 900
    accent_color = colors.HexColor("#2563eb")  # Blue 600
    secondary_color = colors.HexColor("#475569") # Slate 600
    border_color = colors.HexColor("#cbd5e1")
    light_bg = colors.HexColor("#f8fafc")
    card_bg = colors.HexColor("#f1f5f9")
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=accent_color,
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=accent_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=primary_color,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=14,
        bulletIndent=4,
        spaceAfter=4
    )
    
    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=8
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=primary_color
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title Banner
    story.append(Paragraph("FACT KNOWLEDGE LAYER", title_style))
    story.append(Paragraph("Comprehensive Architectural & Technical Specification | Superjoin Engineering Assignment", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceBefore=0, spaceAfter=12))

    # Executive Overview
    story.append(Paragraph("1. Executive Summary & Core Objective", h1_style))
    story.append(Paragraph(
        "The <b>Fact Knowledge Layer</b> is an enterprise-grade, model-agnostic knowledge extraction, grounding, and cross-document reasoning engine. "
        "It ingests arbitrary multi-page PDFs, extracts atomic factual claims into structured semantic triples (<code>subject, predicate, value</code>), "
        "enforces <b>strict verbatim evidence grounding</b> (exact source quotes, page numbers, character offsets), indexes claims with dense vector embeddings, "
        "and resolves inter-document relationships across four critical evaluation cases: <b>Corroboration</b>, <b>Contradiction</b>, <b>Reconciled by Context</b>, and <b>Extraction Failure Defense</b>.",
        body_style
    ))

    # Why, What, How Framework
    story.append(Paragraph("2. Architectural Foundations: The 'Why, What, How' Framework", h1_style))
    
    story.append(Paragraph("A. WHY? — Problem Statement & Industry Bottlenecks", h2_style))
    story.append(Paragraph("• <b>Auditability & Hallucination:</b> Enterprise RAG setups produce conversational summaries without verifiable character-level citations.", bullet_style))
    story.append(Paragraph("• <b>Rigid Domain Schemas:</b> Hardcoded schemas fail when exposed to unseen multi-domain document types (legal, financial, clinical).", bullet_style))
    story.append(Paragraph("• <b>The O(N^2) LLM Cost Bottleneck:</b> Naively performing pairwise LLM comparisons between hundreds of claims across multiple documents scales exponentially in latency and cost.", bullet_style))

    story.append(Paragraph("B. WHAT? — The Proposed Solution", h2_style))
    story.append(Paragraph(
        "A modular, multi-tier knowledge platform that transforms raw unstructured documents into a queryable, vectorized factual knowledge graph with strict mathematical and substring audit trails.",
        body_style
    ))

    story.append(Paragraph("C. HOW? — Technical Pipeline Execution", h2_style))
    story.append(Paragraph("1. <b>PDF Stream Parsing:</b> Page-by-page text stream extraction using <code>pdfplumber</code> and <code>PyMuPDF</code> with layout preservation.", bullet_style))
    story.append(Paragraph("2. <b>Boundary-Aware Semantic Chunking:</b> Text segmentation preserving global character start/end offset pointers.", bullet_style))
    story.append(Paragraph("3. <b>Dynamic Structured Extraction:</b> Pydantic-enforced LLM schema outputting atomic factual triples with time scope and arbitrary attributes.", bullet_style))
    story.append(Paragraph("4. <b>Verbatim Grounding Verification:</b> Mathematical substring matching and fuzzy window repair that rejects hallucinated claims.", bullet_style))
    story.append(Paragraph("5. <b>Dense Embedding & Cosine Pruning:</b> Local dense vectors (<code>sentence-transformers</code>) filter candidate pairs before LLM reasoning, eliminating the O(N^2) bottleneck.", bullet_style))
    story.append(Paragraph("6. <b>Cross-Document Reasoning Engine:</b> Dual-fact comparative contextual analysis classifying relationship types with confidence scores.", bullet_style))

    story.append(Spacer(1, 8))

    # Tech Stack Table
    story.append(Paragraph("3. Technology Stack & Framework Justifications", h1_style))
    
    tech_data = [
        [Paragraph("Layer / Component", table_header_style), Paragraph("Technology / Library", table_header_style), Paragraph("Architectural Justification & Trade-off", table_header_style)],
        [Paragraph("Backend Framework", table_cell_bold), Paragraph("FastAPI + Uvicorn (Async)", table_cell_style), Paragraph("High throughput, native async BackgroundTasks, auto OpenAPI/Swagger docs.", table_cell_style)],
        [Paragraph("LLM Abstraction", table_cell_bold), Paragraph("LangChain Core + Pydantic v2", table_cell_style), Paragraph("Model-agnostic switching (Gemini, OpenAI, Mock) with strict JSON schema enforcement.", table_cell_style)],
        [Paragraph("Embedding Engine", table_cell_bold), Paragraph("Sentence-Transformers (MiniLM-L6)", table_cell_style), Paragraph("Ultra-low latency local inference (384-dim), zero external API cost, high semantic fidelity.", table_cell_style)],
        [Paragraph("PDF Processing", table_cell_bold), Paragraph("pdfplumber + PyMuPDF (fitz)", table_cell_style), Paragraph("Precise character coordinates, page segmentation, robust stream parsing.", table_cell_style)],
        [Paragraph("Persistence Layer", table_cell_bold), Paragraph("SQLAlchemy 2.0 (Postgres / SQLite)", table_cell_style), Paragraph("Zero-setup local SQLite fallback with instant migration path to production PostgreSQL.", table_cell_style)],
        [Paragraph("Frontend UI", table_cell_bold), Paragraph("HTML5 / Modern Vanilla CSS / JS", table_cell_style), Paragraph("Zero-build-step workstation UI, real-time polling, lightweight and responsive.", table_cell_style)],
    ]
    
    t_tech = Table(tech_data, colWidths=[1.4*inch, 1.8*inch, 3.8*inch])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_tech)

    story.append(PageBreak())

    # The 4 Evaluation Cases
    story.append(Paragraph("4. The Four Required Demonstration Cases", h1_style))
    story.append(Paragraph("The system has been evaluated against and successfully handles the four core relationship cases:", body_style))

    cases_data = [
        [Paragraph("Case Scenario", table_header_style), Paragraph("Input Fact Claims", table_header_style), Paragraph("Classification & Reasoning Logic", table_header_style)],
        
        [
            Paragraph("<b>Case 1:<br/>Corroboration</b>", table_cell_style),
            Paragraph("<b>Doc 1:</b> 'Acme Corp recorded annual revenue of $120M in FY23.'<br/><b>Doc 2:</b> 'Acme Corp reported $120 million in top-line revenue for FY 2023.'", table_cell_style),
            Paragraph("<b>Result: CORROBORATION</b><br/>Confirms identical financial metrics ($120M) for the exact same entity and temporal window despite phrasing differences.", table_cell_style)
        ],
        [
            Paragraph("<b>Case 2:<br/>Contradiction</b>", table_cell_style),
            Paragraph("<b>Doc 1:</b> 'Dr. Aris Thorne served as Lead Research Officer throughout 2024.'<br/><b>Doc 3:</b> 'Dr. Thorne formally resigned and vacated all roles on Jan 15, 2024.'", table_cell_style),
            Paragraph("<b>Result: CONTRADICTION</b><br/>Identifies mutually exclusive employment status claims for the same individual during the same calendar period.", table_cell_style)
        ],
        [
            Paragraph("<b>Case 3:<br/>Reconciled by Context</b>", table_cell_style),
            Paragraph("<b>Doc 1:</b> 'Acme Corp FY23 Revenue: $120M.'<br/><b>Doc 2:</b> 'Acme Corp FY24 Revenue: $155M.'", table_cell_style),
            Paragraph("<b>Result: RECONCILED_BY_CONTEXT</b><br/>Resolves apparent numerical discrepancy by analyzing distinct temporal scopes (FY23 vs FY24 revenue growth).", table_cell_style)
        ],
        [
            Paragraph("<b>Case 4:<br/>Failure Handling & Defense</b>", table_cell_style),
            Paragraph("<b>Source:</b> 'Trial enrolled 450 subjects.'<br/><b>Hallucinated:</b> 'Trial tested 4500 patients.'", table_cell_style),
            Paragraph("<b>Result: FAILURE_HANDLING (Rejected)</b><br/>Strict grounding validator verifies verbatim substrings. Rejects hallucinated/unfounded claims to safeguard knowledge integrity.", table_cell_style)
        ]
    ]

    t_cases = Table(cases_data, colWidths=[1.3*inch, 2.7*inch, 3.0*inch])
    t_cases.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_cases)

    story.append(Spacer(1, 10))

    # Production Architecture & Scalability
    story.append(Paragraph("5. Production-Ready Target Architecture & Next Steps", h1_style))
    story.append(Paragraph("To scale this prototype to billions of documents across enterprise clusters, the target production architecture incorporates:", body_style))
    
    story.append(Paragraph("• <b>Distributed Job Processing:</b> Replace in-memory BackgroundTasks with Celery / Temporal workers backed by Redis or RabbitMQ queues for horizontal worker autoscaling.", bullet_style))
    story.append(Paragraph("• <b>Dedicated Vector & Graph Storage:</b> Integrate pgvector / Qdrant for billion-scale vector indexing and Neo4j for multi-hop graph relationship traversals (GraphRAG).", bullet_style))
    story.append(Paragraph("• <b>Multimodal OCR & Table Parsing:</b> Incorporate LayoutLM / Table Transformer models with visual bounding-box coordinate tracking for scanned documents.", bullet_style))
    story.append(Paragraph("• <b>Real-Time Event Streaming:</b> Stream incremental extraction events directly to the UI via Server-Sent Events (SSE) or WebSockets as pages are processed.", bullet_style))

    story.append(Spacer(1, 10))

    # Video Demo Script & Timing
    story.append(Paragraph("6. 3-Minute Video Demo Structure & Script", h1_style))
    story.append(Paragraph("Use this structured timing guide when recording the submission demo video:", body_style))
    story.append(Paragraph("• <b>0:00 - 0:40 | Introduction & Architecture:</b> State the problem (auditability, hallucinations, O(N^2) costs) and show the pipeline architecture diagram.", bullet_style))
    story.append(Paragraph("• <b>0:40 - 1:20 | PDF Ingestion & Grounding:</b> Upload a sample PDF, inspect background task completion, and highlight exact character offsets + verbatim quotes.", bullet_style))
    story.append(Paragraph("• <b>1:20 - 2:30 | 4 Demonstration Cases:</b> Walk through Corroboration, Contradiction, Reconciled by Context, and Grounding Failure Rejection.", bullet_style))
    story.append(Paragraph("• <b>2:30 - 3:00 | API & Conclusion:</b> Showcase Swagger docs (<code>/docs</code>), persistence in DB, and summarize production scalability roadmap.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF generated successfully:", filename)

if __name__ == "__main__":
    build_pdf()
