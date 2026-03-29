"""Generate TAMS-branded PowerPoint presentations using the official template."""

import os
import re
import copy
from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

from config import TAMS_PPTX_TEMPLATE, TAMS_DEEP_BLUE, TAMS_LIGHT_BLUE

# Brand colors
DEEP_BLUE = RGBColor(0x22, 0x2F, 0x62)
LIGHT_BLUE = RGBColor(0x1A, 0x6D, 0xB6)
TURQUOISE = RGBColor(0x6C, 0xB9, 0xB6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK_CARBON = RGBColor(0x0E, 0x1A, 0x24)
SOFT_CARBON = RGBColor(0xB1, 0xB3, 0xB6)
GRAY = RGBColor(0x4A, 0x4A, 0x4A)

# Template layout indices
LAYOUT_TITLE = 0          # "Title Slide" - has CENTER_TITLE + SUBTITLE
LAYOUT_TITLE_ONLY = 1     # "Title Only" - has TITLE placeholder
LAYOUT_BLANK = 2          # "Blank" - branded but no placeholders
LAYOUT_TAM_BG = 3         # "Tam Background" - full branded background
LAYOUT_EMPTY = 7          # "5_Custom Layout" - empty layout
LAYOUT_BLANK_PAGE = 23    # "Balnk Page" - clean blank


def _delete_all_slides(prs):
    """Delete all existing slides from the presentation, keeping layouts and masters."""
    while len(prs.slides) > 0:
        rId = prs.slides._sldIdLst[0].get(qn('r:id'))
        prs.part.drop_rel(rId)
        prs.slides._sldIdLst.remove(prs.slides._sldIdLst[0])


def _add_textbox(slide, left, top, width, height, text, font_size=11,
                 font_color=GRAY, bold=False, alignment=PP_ALIGN.LEFT, font_name="Arial"):
    """Add a text box to a slide."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = alignment
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.color.rgb = font_color
    run.font.bold = bold
    run.font.name = font_name
    return txBox


def _add_cover_slide(prs, stock_name, ticker, date_str):
    """Add cover slide using the official template layout."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE])

    # Populate title placeholder
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:  # CENTER_TITLE
            ph.text = stock_name.upper()
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(36)
                    run.font.bold = True
                    run.font.color.rgb = WHITE
        elif ph.placeholder_format.idx == 1:  # SUBTITLE
            ph.text = f"({ticker})\nComprehensive Investor Report\n{date_str}"
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(16)
                    run.font.color.rgb = SOFT_CARBON

    return slide


def _add_toc_slide(prs, sections):
    """Add a Table of Contents slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE_ONLY])

    # Set title
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:
            ph.text = "TABLE OF CONTENTS"
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(28)
                    run.font.bold = True
                    run.font.color.rgb = DEEP_BLUE

    # Add section list
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

    toc_text = ""
    for i, (key, title) in enumerate(section_titles.items(), 1):
        if key in sections:
            toc_text += f"{i}.  {title}\n"

    _add_textbox(slide, Inches(1), Inches(2), Inches(10), Inches(4.5),
                 toc_text, font_size=14, font_color=GRAY)

    return slide


def _parse_content_to_paragraphs(content, max_lines=16):
    """Parse markdown content into structured paragraphs for slides."""
    lines = content.strip().split("\n")
    paragraphs = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("|"):
            continue  # Skip markdown tables (too complex for slides)
        if line.startswith("## "):
            paragraphs.append({"text": line[3:].strip(), "type": "heading", "level": 2})
        elif line.startswith("### "):
            paragraphs.append({"text": line[4:].strip(), "type": "heading", "level": 3})
        elif line.startswith("#### "):
            paragraphs.append({"text": line[5:].strip(), "type": "heading", "level": 4})
        elif line.startswith("- ") or line.startswith("* "):
            paragraphs.append({"text": line[2:].replace("**", ""), "type": "bullet"})
        elif re.match(r'^\d+\.\s+', line):
            text = re.sub(r'^\d+\.\s+', '', line).replace("**", "")
            paragraphs.append({"text": text, "type": "numbered"})
        else:
            paragraphs.append({"text": line.replace("**", ""), "type": "body"})

    return paragraphs


def _add_content_slide(prs, title, content, chart_path=None):
    """Add a content slide with title and body text."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE_ONLY])

    # Set title
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:
            ph.text = title
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(24)
                    run.font.bold = True
                    run.font.color.rgb = DEEP_BLUE

    # Content area dimensions (13.33" wide slide)
    content_left = Inches(0.8)
    content_top = Inches(1.8)
    content_width = Inches(11.5)
    content_height = Inches(5)

    if chart_path and os.path.exists(chart_path):
        # Split: text left, chart right
        content_width = Inches(5.5)
        try:
            slide.shapes.add_picture(chart_path, Inches(6.8), Inches(1.8), width=Inches(5.5))
        except Exception:
            content_width = Inches(11.5)  # Fallback to full width

    # Add body content
    paragraphs = _parse_content_to_paragraphs(content, max_lines=16)
    if not paragraphs:
        return slide

    txBox = slide.shapes.add_textbox(content_left, content_top, content_width, content_height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, para in enumerate(paragraphs[:16]):  # Max 16 items per slide
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        p.space_before = Pt(2)
        p.space_after = Pt(2)

        if para["type"] == "heading":
            run = p.add_run()
            run.text = para["text"]
            run.font.size = Pt(14 if para["level"] == 2 else 12)
            run.font.bold = True
            run.font.color.rgb = DEEP_BLUE
            run.font.name = "Arial"
            p.space_before = Pt(8)
        elif para["type"] == "bullet":
            run = p.add_run()
            run.text = f"  \u2022  {para['text']}"
            run.font.size = Pt(10)
            run.font.color.rgb = GRAY
            run.font.name = "Arial"
        elif para["type"] == "numbered":
            run = p.add_run()
            run.text = f"     {para['text']}"
            run.font.size = Pt(10)
            run.font.color.rgb = GRAY
            run.font.name = "Arial"
        else:
            run = p.add_run()
            run.text = para["text"]
            run.font.size = Pt(10)
            run.font.color.rgb = GRAY
            run.font.name = "Arial"

    return slide


def _add_sources_slide(prs, sources_text):
    """Add a Sources & References slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE_ONLY])

    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:
            ph.text = "SOURCES & REFERENCES"
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(24)
                    run.font.bold = True
                    run.font.color.rgb = DEEP_BLUE

    _add_textbox(slide, Inches(0.8), Inches(1.8), Inches(11.5), Inches(5),
                 sources_text, font_size=9, font_color=GRAY)

    return slide


def _add_disclaimer_slide(prs):
    """Add a disclaimer slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[LAYOUT_TITLE])

    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:
            ph.text = "Disclaimer"
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(28)
                    run.font.bold = True
                    run.font.color.rgb = WHITE
        elif ph.placeholder_format.idx == 1:
            ph.text = (
                "This document is for informational purposes only and does not constitute "
                "investment advice. Past performance does not guarantee future results. "
                "TAM Capital and its affiliates may hold positions in the securities discussed. "
                "TAM Capital is regulated by the Capital Market Authority (CMA) of Saudi Arabia."
            )
            for para in ph.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(12)
                    run.font.color.rgb = SOFT_CARBON

    return slide


def generate_pptx_report(stock_name: str, ticker: str, sections: dict,
                         charts: dict = None, output_dir: str = "output",
                         sources=None) -> str:
    """Generate a TAMS-branded PPTX presentation using the official template.

    Args:
        stock_name: Company name
        ticker: Stock ticker
        sections: Dict of section_name -> content text
        charts: Dict of chart_name -> chart file path
        output_dir: Output directory
        sources: SourceCollector instance or formatted string

    Returns:
        Path to generated PPTX file
    """
    os.makedirs(output_dir, exist_ok=True)

    # Open official template
    if os.path.exists(TAMS_PPTX_TEMPLATE):
        prs = Presentation(TAMS_PPTX_TEMPLATE)
        _delete_all_slides(prs)
    else:
        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

    date_str = datetime.now().strftime("%B %d, %Y")

    # 1. Cover slide
    _add_cover_slide(prs, stock_name, ticker, date_str)

    # 2. Section slides
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

    chart_map = {
        "fundamental_analysis": "revenue_earnings",
        "technical_analysis": "technical",
        "dividend_analysis": "dividend",
    }

    section_order = [
        "executive_summary", "fundamental_analysis", "dividend_analysis",
        "earnings_analysis", "risk_assessment", "technical_analysis",
        "sector_rotation", "news_impact", "war_impact", "key_takeaways"
    ]

    for section_key in section_order:
        if section_key not in sections:
            continue

        title = section_titles.get(section_key, section_key.replace("_", " ").title())
        content = sections[section_key]
        chart_path = None
        if charts:
            chart_key = chart_map.get(section_key)
            if chart_key:
                chart_path = charts.get(chart_key)

        # Split long content into multiple slides
        lines = content.strip().split("\n")
        chunk_size = 16
        for chunk_start in range(0, len(lines), chunk_size):
            chunk = "\n".join(lines[chunk_start:chunk_start + chunk_size])
            slide_title = title if chunk_start == 0 else f"{title} (cont.)"
            _add_content_slide(prs, slide_title, chunk,
                              chart_path if chunk_start == 0 else None)

    # 4. Sources slide
    if sources:
        if hasattr(sources, 'format_for_pptx'):
            sources_text = sources.format_for_pptx()
        else:
            sources_text = str(sources)
        _add_sources_slide(prs, sources_text)

    # 5. Disclaimer slide
    _add_disclaimer_slide(prs)

    # Save
    safe_name = re.sub(r'[^\w\s-]', '', stock_name).strip().replace(" ", "_")
    filename = f"{safe_name}_Investor_Report_TAM_{datetime.now().strftime('%Y%m%d')}.pptx"
    filepath = os.path.join(output_dir, filename)
    prs.save(filepath)

    return filepath
