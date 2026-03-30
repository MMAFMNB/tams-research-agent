"""Generate TAMS-branded PDF reports using ReportLab, with docx2pdf fallback."""

import os
import re
import subprocess
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageBreak, KeepTogether, NextPageTemplate, PageTemplate, Frame,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import TAMS_LOGO, TAMS_FOOTER, ASSETS_DIR

# ---------- Brand colors ----------
TAM_DEEP_BLUE = HexColor("#222F62")
TAM_LIGHT_BLUE = HexColor("#1A6DB6")
TAM_TURQUOISE = HexColor("#6CB9B6")
TAM_SOFT_CARBON = HexColor("#B1B3B6")
TAM_DARK_CARBON = HexColor("#0E1A24")
TAM_GRAY = HexColor("#4A4A4A")
TAM_LIGHT_BLUE_BG = HexColor("#E8F0F8")
TAM_WHITE = white

# ---------- Font registration ----------
_FONTS_REGISTERED = False


def _register_fonts():
    """Register fonts once. Uses Helvetica (built-in) as primary."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    # Try to register Arial if available on system
    for arial_path in [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]:
        if os.path.exists(arial_path):
            try:
                pdfmetrics.registerFont(TTFont("Arial", arial_path))
                bold_path = arial_path.replace("arial", "arialbd").replace("Arial", "ArialBold")
                if not os.path.exists(bold_path):
                    bold_path = arial_path.replace(".ttf", "bd.ttf")
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("Arial-Bold", bold_path))
                break
            except Exception:
                pass
    _FONTS_REGISTERED = True


def _font(bold=False):
    """Return the best available font name."""
    try:
        pdfmetrics.getFont("Arial")
        return "Arial-Bold" if bold else "Arial"
    except KeyError:
        return "Helvetica-Bold" if bold else "Helvetica"


# ---------- Styles ----------
def _create_styles():
    """Create TAM-branded paragraph styles."""
    _register_fonts()
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TAM_Title",
        fontName=_font(bold=True),
        fontSize=26,
        textColor=TAM_DEEP_BLUE,
        spaceAfter=6,
        leading=32,
    ))
    styles.add(ParagraphStyle(
        name="TAM_Subtitle",
        fontName=_font(),
        fontSize=14,
        textColor=TAM_GRAY,
        spaceAfter=4,
        leading=18,
    ))
    styles.add(ParagraphStyle(
        name="TAM_H1",
        fontName=_font(bold=True),
        fontSize=18,
        textColor=TAM_DEEP_BLUE,
        spaceBefore=20,
        spaceAfter=10,
        leading=22,
    ))
    styles.add(ParagraphStyle(
        name="TAM_H2",
        fontName=_font(bold=True),
        fontSize=14,
        textColor=TAM_DEEP_BLUE,
        spaceBefore=14,
        spaceAfter=6,
        leading=18,
    ))
    styles.add(ParagraphStyle(
        name="TAM_H3",
        fontName=_font(bold=True),
        fontSize=12,
        textColor=TAM_LIGHT_BLUE,
        spaceBefore=10,
        spaceAfter=4,
        leading=15,
    ))
    styles.add(ParagraphStyle(
        name="TAM_H4",
        fontName=_font(bold=True),
        fontSize=10,
        textColor=TAM_DEEP_BLUE,
        spaceBefore=8,
        spaceAfter=3,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        name="TAM_Body",
        fontName=_font(),
        fontSize=9,
        textColor=TAM_GRAY,
        spaceAfter=4,
        leading=13,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name="TAM_Bullet",
        fontName=_font(),
        fontSize=9,
        textColor=TAM_GRAY,
        spaceAfter=3,
        leading=12,
        leftIndent=18,
        bulletIndent=6,
    ))
    styles.add(ParagraphStyle(
        name="TAM_Small",
        fontName=_font(),
        fontSize=7,
        textColor=TAM_SOFT_CARBON,
        spaceAfter=2,
        leading=9,
    ))
    styles.add(ParagraphStyle(
        name="TAM_TOC_Entry",
        fontName=_font(),
        fontSize=11,
        textColor=TAM_GRAY,
        spaceBefore=4,
        spaceAfter=4,
        leading=16,
        leftIndent=10,
    ))
    styles.add(ParagraphStyle(
        name="TAM_Disclaimer",
        fontName=_font(),
        fontSize=8,
        textColor=TAM_GRAY,
        spaceAfter=6,
        leading=11,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name="TAM_Footer",
        fontName=_font(),
        fontSize=7,
        textColor=TAM_SOFT_CARBON,
    ))
    return styles


# ---------- RTL Detection ----------
def _detect_rtl(text):
    """Detect if text contains Arabic characters."""
    for ch in text:
        if '\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F':
            return True
        if '\uFB50' <= ch <= '\uFDFF' or '\uFE70' <= ch <= '\uFEFF':
            return True
    return False


# ---------- Page callbacks ----------
def _header_footer(canvas, doc, date_str, logo_path):
    """Draw header logo + footer on every page (except cover)."""
    canvas.saveState()
    page_w, page_h = A4

    # Header: TAM logo top-right
    if logo_path and os.path.exists(logo_path):
        logo_w = 1.2 * inch
        logo_h = 0.4 * inch
        canvas.drawImage(
            logo_path,
            page_w - 1.8 * cm - logo_w, page_h - 1.5 * cm,
            width=logo_w, height=logo_h,
            preserveAspectRatio=True, mask="auto",
        )

    # Thin header line
    canvas.setStrokeColor(TAM_SOFT_CARBON)
    canvas.setLineWidth(0.5)
    canvas.line(1.8 * cm, page_h - 2.0 * cm, page_w - 1.8 * cm, page_h - 2.0 * cm)

    # Footer line
    canvas.line(1.8 * cm, 1.8 * cm, page_w - 1.8 * cm, 1.8 * cm)

    # Footer left: TAM Capital | CMA Licensed
    canvas.setFont(_font(), 7)
    canvas.setFillColor(TAM_SOFT_CARBON)
    canvas.drawString(1.8 * cm, 1.2 * cm, "TAM Capital  |  CMA Licensed")

    # Footer center: date
    canvas.drawCentredString(page_w / 2, 1.2 * cm, date_str)

    # Footer right: page number
    canvas.drawRightString(page_w - 1.8 * cm, 1.2 * cm, f"Page {doc.page}")

    canvas.restoreState()


def _cover_page_callback(canvas, doc):
    """Cover page has no header/footer."""
    pass


# ---------- Content parsing ----------
def _parse_markdown_table(text):
    """Parse markdown table text into headers + rows."""
    lines = text.strip().split("\n")
    rows = []
    for line in lines:
        line = line.strip()
        if not line or (line.startswith("|") and set(line.replace("|", "").strip()) <= {"-", ":"}):
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            rows.append(cells)
    return rows


def _build_table(rows, styles, available_width):
    """Build a ReportLab Table from parsed markdown table rows."""
    if not rows or len(rows) < 2:
        return None

    num_cols = len(rows[0])
    col_width = available_width / num_cols

    # Convert cells to Paragraphs
    table_data = []
    for i, row in enumerate(rows):
        table_row = []
        for cell_text in row[:num_cols]:
            if i == 0:
                p = Paragraph(
                    f"<b>{cell_text}</b>",
                    ParagraphStyle("cell_hdr", parent=styles["TAM_Small"],
                                   textColor=TAM_WHITE, fontSize=8,
                                   alignment=TA_CENTER, fontName=_font(bold=True))
                )
            else:
                p = Paragraph(
                    cell_text,
                    ParagraphStyle("cell", parent=styles["TAM_Small"],
                                   fontSize=8, alignment=TA_CENTER)
                )
            table_row.append(p)
        table_data.append(table_row)

    tbl = Table(table_data, colWidths=[col_width] * num_cols)

    style_cmds = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), TAM_DEEP_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), TAM_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), _font(bold=True)),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, TAM_SOFT_CARBON),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Alternating row colors
    for row_idx in range(1, len(table_data)):
        if row_idx % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), TAM_LIGHT_BLUE_BG))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _markdown_to_flowables(content, styles, charts=None, chart_key=None,
                           available_width=None):
    """Convert markdown-ish section content to ReportLab flowables."""
    if available_width is None:
        available_width = A4[0] - 3.6 * cm

    flowables = []
    lines = content.split("\n")
    in_table = False
    table_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Table detection
        if line.strip().startswith("|") and not in_table:
            in_table = True
            table_lines = [line]
            i += 1
            continue
        if in_table and line.strip().startswith("|"):
            table_lines.append(line)
            i += 1
            continue
        if in_table and not line.strip().startswith("|"):
            in_table = False
            tbl = _build_table(_parse_markdown_table("\n".join(table_lines)),
                               styles, available_width)
            if tbl:
                flowables.append(Spacer(1, 6))
                flowables.append(tbl)
                flowables.append(Spacer(1, 6))
            table_lines = []

        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # Horizontal rules
        if stripped.startswith("---") or stripped.startswith("==="):
            i += 1
            continue

        # Headings
        if stripped.startswith("## "):
            flowables.append(Paragraph(stripped[3:], styles["TAM_H2"]))
            i += 1
            continue
        if stripped.startswith("### "):
            flowables.append(Paragraph(stripped[4:], styles["TAM_H3"]))
            i += 1
            continue
        if stripped.startswith("#### "):
            flowables.append(Paragraph(stripped[5:], styles["TAM_H4"]))
            i += 1
            continue

        # Bold-only lines
        if stripped.startswith("**") and stripped.endswith("**"):
            text = stripped[2:-2]
            flowables.append(Paragraph(f"<b>{text}</b>", styles["TAM_Body"]))
            i += 1
            continue

        # Bullet points
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = _inline_bold(stripped[2:])
            flowables.append(Paragraph(
                f"\u2022  {text}", styles["TAM_Bullet"]
            ))
            i += 1
            continue

        # Numbered items
        m = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if m:
            text = _inline_bold(m.group(2))
            flowables.append(Paragraph(
                f"{m.group(1)}.  {text}", styles["TAM_Bullet"]
            ))
            i += 1
            continue

        # Regular body text
        text = _inline_bold(stripped)
        flowables.append(Paragraph(text, styles["TAM_Body"]))
        i += 1

    # Trailing table
    if in_table and table_lines:
        tbl = _build_table(_parse_markdown_table("\n".join(table_lines)),
                           styles, available_width)
        if tbl:
            flowables.append(tbl)

    return flowables


def _inline_bold(text):
    """Convert **bold** markdown to <b>bold</b> for ReportLab Paragraphs."""
    return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)


# ---------- Cover page flowables ----------
def _build_cover(stock_name, ticker, date_str, styles):
    """Build cover page flowables."""
    elements = []

    elements.append(Spacer(1, 2.5 * inch))

    # Company name
    elements.append(Paragraph(stock_name.upper(), styles["TAM_Title"]))

    # Ticker
    elements.append(Paragraph(
        f"({ticker})",
        ParagraphStyle("ticker", parent=styles["TAM_Subtitle"],
                       textColor=TAM_LIGHT_BLUE, fontSize=14)
    ))
    elements.append(Spacer(1, 18))

    # Accent line
    line_tbl = Table([[""]], colWidths=[2.5 * inch], rowHeights=[3])
    line_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TAM_TURQUOISE),
        ("LINEBELOW", (0, 0), (-1, -1), 0, TAM_TURQUOISE),
    ]))
    elements.append(line_tbl)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("Comprehensive Investor Report", styles["TAM_H2"]))
    elements.append(Paragraph(
        "Equity Analysis, News Impact Assessment &amp; Geopolitical Risk Assessment",
        styles["TAM_Subtitle"]
    ))
    elements.append(Spacer(1, 30))

    # Metadata
    meta = [
        ("Date:", date_str),
        ("Prepared by:", "TAM Capital"),
        ("Classification:", "Confidential \u2014 For Investor Use Only"),
    ]
    for label, value in meta:
        elements.append(Paragraph(
            f"<b>{label}</b>  {value}", styles["TAM_Body"]
        ))

    elements.append(PageBreak())
    return elements


# ---------- TOC ----------
def _build_toc(sections, styles):
    """Build a Table of Contents page."""
    elements = []
    elements.append(Paragraph("TABLE OF CONTENTS", styles["TAM_H1"]))
    elements.append(Spacer(1, 12))

    section_titles = {
        "executive_summary": "Executive Summary",
        "fundamental_analysis": "Fundamental Analysis",
        "dividend_analysis": "Dividend Income Analysis",
        "earnings_analysis": "Earnings Analysis",
        "risk_assessment": "Risk Assessment Framework",
        "technical_analysis": "Technical Analysis Dashboard",
        "sector_rotation": "Sector Rotation Strategy",
        "news_impact": "News Impact Assessment",
        "war_impact": "Geopolitical Risk Assessment",
        "key_takeaways": "Key Takeaways & Investment Thesis",
    }
    section_order = [
        "executive_summary", "fundamental_analysis", "dividend_analysis",
        "earnings_analysis", "risk_assessment", "technical_analysis",
        "sector_rotation", "news_impact", "war_impact", "key_takeaways",
    ]

    num = 1
    for key in section_order:
        if key in sections:
            title = section_titles.get(key, key.replace("_", " ").title())
            elements.append(Paragraph(
                f'<font color="#1A6DB6"><b>{num:02d}</b></font>'
                f'&nbsp;&nbsp;&nbsp;&nbsp;{title}',
                styles["TAM_TOC_Entry"]
            ))
            num += 1

    elements.append(PageBreak())
    return elements


# ---------- Main generator ----------
def generate_pdf_report(stock_name: str, ticker: str, sections: dict,
                        charts: dict = None, output_dir: str = "output",
                        sources=None) -> str:
    """Generate a TAMS-branded PDF report using ReportLab.

    Args:
        stock_name: Company name
        ticker: Stock ticker
        sections: Dict of section_name -> content text
        charts: Dict of chart_name -> chart file path
        output_dir: Output directory
        sources: SourceCollector instance or formatted string

    Returns:
        Path to generated PDF file
    """
    _register_fonts()
    os.makedirs(output_dir, exist_ok=True)

    safe_name = re.sub(r'[^\w\s-]', '', stock_name).strip().replace(" ", "_")
    filename = f"{safe_name}_Investor_Report_TAM_{datetime.now().strftime('%Y%m%d')}.pdf"
    filepath = os.path.join(output_dir, filename)

    date_str = datetime.now().strftime("%B %d, %Y")
    styles = _create_styles()
    page_w, page_h = A4

    # Build page templates
    content_frame = Frame(
        1.8 * cm, 2.2 * cm,
        page_w - 3.6 * cm, page_h - 4.4 * cm,
        id="content"
    )
    cover_frame = Frame(
        1.8 * cm, 2.2 * cm,
        page_w - 3.6 * cm, page_h - 4.4 * cm,
        id="cover"
    )

    logo_path = TAMS_LOGO if os.path.exists(TAMS_LOGO) else None

    def _on_page(canvas, doc):
        _header_footer(canvas, doc, date_str, logo_path)

    cover_template = PageTemplate(
        id="Cover",
        frames=[cover_frame],
        onPage=_cover_page_callback,
    )
    content_template = PageTemplate(
        id="Content",
        frames=[content_frame],
        onPage=_on_page,
    )

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        title=f"{stock_name} ({ticker}) - Investor Report",
        author="TAM Capital",
        subject="Investment Research Report",
        creator="TAM Capital Research Agent",
    )
    doc.addPageTemplates([cover_template, content_template])

    available_width = page_w - 3.6 * cm

    # ---------- Assemble elements ----------
    elements = []

    # Cover page (uses Cover template)
    elements.extend(_build_cover(stock_name, ticker, date_str, styles))

    # Switch to Content template for remaining pages
    elements.append(NextPageTemplate("Content"))

    # Table of Contents
    elements.extend(_build_toc(sections, styles))

    # Section mappings
    section_titles = {
        "executive_summary": "Executive Summary",
        "fundamental_analysis": "Fundamental Analysis",
        "dividend_analysis": "Dividend Income Analysis",
        "earnings_analysis": "Earnings Analysis",
        "risk_assessment": "Risk Assessment Framework",
        "technical_analysis": "Technical Analysis Dashboard",
        "sector_rotation": "Sector Rotation Strategy",
        "news_impact": "News Impact Assessment",
        "war_impact": "Geopolitical Risk Assessment",
        "key_takeaways": "Key Takeaways &amp; Investment Thesis",
    }
    section_order = [
        "executive_summary", "fundamental_analysis", "dividend_analysis",
        "earnings_analysis", "risk_assessment", "technical_analysis",
        "sector_rotation", "news_impact", "war_impact", "key_takeaways",
    ]
    chart_map = {
        "fundamental_analysis": "revenue_earnings",
        "technical_analysis": "technical",
        "dividend_analysis": "dividend",
    }

    # Content sections
    for section_key in section_order:
        if section_key not in sections:
            continue

        title = section_titles.get(section_key, section_key.replace("_", " ").title())
        content = sections[section_key]

        # Section heading
        elements.append(Paragraph(title.upper(), styles["TAM_H1"]))

        # Accent underline
        line_tbl = Table([[""]], colWidths=[1.5 * inch], rowHeights=[2])
        line_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), TAM_TURQUOISE),
        ]))
        elements.append(line_tbl)
        elements.append(Spacer(1, 8))

        # Section body
        flowables = _markdown_to_flowables(content, styles,
                                           available_width=available_width)
        elements.extend(flowables)

        # Chart for this section
        if charts:
            chart_key = chart_map.get(section_key)
            if chart_key:
                chart_path = charts.get(chart_key, "")
                if chart_path and os.path.exists(chart_path):
                    elements.append(Spacer(1, 12))
                    img_width = min(available_width, 5 * inch)
                    elements.append(Image(chart_path, width=img_width,
                                          height=img_width * 0.625))
                    elements.append(Spacer(1, 8))

        elements.append(PageBreak())

    # Sources & References
    if sources:
        elements.append(Paragraph("SOURCES &amp; REFERENCES", styles["TAM_H1"]))
        line_tbl = Table([[""]], colWidths=[1.5 * inch], rowHeights=[2])
        line_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), TAM_TURQUOISE),
        ]))
        elements.append(line_tbl)
        elements.append(Spacer(1, 8))

        if hasattr(sources, 'format_for_docx'):
            source_list = sources.format_for_docx()
            groups = {}
            for s in source_list:
                stype = {
                    "yahoo_finance": "Market Data (Yahoo Finance)",
                    "financial_statements": "Financial Statements (Yahoo Finance)",
                    "news_article": "News &amp; Analysis",
                    "web_search": "Web Research",
                    "sector_news": "Sector Research",
                }.get(s["type"], "Other Sources")
                groups.setdefault(stype, []).append(s)

            for group_name, group_sources in groups.items():
                elements.append(Paragraph(f"<b>{group_name}</b>", styles["TAM_Body"]))
                for s in group_sources:
                    text = f"[{s['index']}] {s['title']}"
                    if s.get("url"):
                        text += f'  <font color="#1A6DB6" size="7">{s["url"]}</font>'
                    elements.append(Paragraph(f"\u2022  {text}", styles["TAM_Bullet"]))
        elif hasattr(sources, 'format_for_pptx'):
            elements.append(Paragraph(sources.format_for_pptx(), styles["TAM_Small"]))
        else:
            elements.append(Paragraph(str(sources), styles["TAM_Small"]))

        elements.append(PageBreak())

    # Disclaimer
    elements.append(Paragraph("DISCLAIMER", styles["TAM_H1"]))
    line_tbl = Table([[""]], colWidths=[1.5 * inch], rowHeights=[2])
    line_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TAM_TURQUOISE),
    ]))
    elements.append(line_tbl)
    elements.append(Spacer(1, 8))

    from prompts.report_compiler import DISCLAIMER_TEXT
    for para_text in DISCLAIMER_TEXT.strip().split("\n\n"):
        para_text = para_text.strip()
        if para_text and not para_text.startswith("DISCLAIMER"):
            elements.append(Paragraph(para_text, styles["TAM_Disclaimer"]))

    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Copyright \u00a9 {datetime.now().year} TAM Capital. All rights reserved.",
        ParagraphStyle("copy", parent=styles["TAM_Small"], alignment=TA_CENTER)
    ))

    # Build PDF
    doc.build(elements)
    return filepath


# ---------- Legacy fallback ----------
def convert_docx_to_pdf(docx_path: str) -> str:
    """Convert a DOCX file to PDF (fallback method).

    Tries docx2pdf first (uses Microsoft Word if available),
    falls back to LibreOffice.
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")

    pdf_path = docx_path.replace(".docx", ".pdf")

    # Try docx2pdf (requires Microsoft Word installed)
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
        if os.path.exists(pdf_path):
            return pdf_path
    except Exception:
        pass

    # Try LibreOffice
    try:
        output_dir = os.path.dirname(docx_path)
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf",
             "--outdir", output_dir, docx_path],
            capture_output=True, text=True, timeout=60
        )
        if os.path.exists(pdf_path):
            return pdf_path
    except Exception:
        pass

    raise RuntimeError(
        "Could not convert to PDF. Please install Microsoft Word or LibreOffice.\n"
        "The DOCX file has been generated successfully and can be opened directly."
    )
