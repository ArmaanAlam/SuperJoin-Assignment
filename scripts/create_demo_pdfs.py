import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_pdf(filename: str, title: str, paragraphs: list):
    output_dir = Path("./data/demo_pdfs")
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=14
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10
    )

    story = [
        Paragraph(title, title_style),
        Spacer(1, 10)
    ]

    for p in paragraphs:
        story.append(Paragraph(p, body_style))
        story.append(Spacer(1, 8))

    doc.build(story)
    return str(pdf_path)

def create_all_demo_pdfs():
    """Generates fresh demo PDFs, removing any existing PDFs first."""
    output_dir = Path("./data/demo_pdfs")
    # Remove existing PDFs to ensure a clean start
    if output_dir.exists():
        for existing_file in output_dir.iterdir():
            if existing_file.is_file():
                existing_file.unlink()
    # Recreate the directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # PDF 1: Annual Report (Baseline)
    pdf1_path = create_pdf(
        filename="company_a_annual_report_2024.pdf",
        title="Company A - Annual Report 2024",
        paragraphs=[
            "Company A is a leading technology solutions provider headquartered in the United States.",
            "In our governance update, John Smith resigned as director on March 15, 2024 following five years of exemplary service on the board.",
            "Our financial performance showed sustained momentum throughout the year. Q3 2024 revenue was $5.2M, driven by enterprise cloud adoption.",
            "Corporate Operations: The company maintains its Headquarters in Austin, Texas, overseeing global research and customer success initiatives."
        ]
    )

    # PDF 2: Industry News Article (Corroborations + Reconcilable Time Scope)
    pdf2_path = create_pdf(
        filename="industry_news_article.pdf",
        title="Tech Industry Daily - Market Review 2024",
        paragraphs=[
            "Leadership changes continue to shape the enterprise software landscape this season.",
            "According to official regulatory filings, John Smith stepped down from Company A's board in March 2024.",
            "Market analysis confirms that Company A reported Q3 revenue of $5.2 million, meeting consensus expectations among institutional analysts.",
            "On an annualized basis, Global revenue reached $20M in 2024, reflecting broad-based geographic expansion across APAC and EMEA."
        ]
    )

    # PDF 4: Intentional Unit Normalization Failure Case
    pdf4_path = create_pdf(
        filename="unit_normalization_test_case.pdf",
        title="Company A Financial Note - Unit Representation",
        paragraphs=[
            "Supplementary financial disclosure for statutory filings.",
            "Quarterly reconciliation note: Revenue: 5000 thousand USD for standard operations.",
            "This document tests unit conversion boundaries between thousand USD and million USD."
        ]
    )

    return [pdf1_path, pdf2_path, pdf4_path]

if __name__ == "__main__":
    generated = create_all_demo_pdfs()
    print(f"Generated {len(generated)} demo PDFs:")
    for g in generated:
        print(f" - {g}")
