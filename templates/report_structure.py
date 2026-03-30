"""Report structure definitions and section ordering."""

import re

# Canonical section titles used across all generators and comparators
SECTION_TITLES = {
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

SECTION_ORDER = [
    "executive_summary", "fundamental_analysis", "dividend_analysis",
    "earnings_analysis", "risk_assessment", "technical_analysis",
    "sector_rotation", "news_impact", "war_impact", "key_takeaways",
]

CHART_MAP = {
    "fundamental_analysis": "revenue_earnings",
    "technical_analysis": "technical",
    "dividend_analysis": "dividend",
}


def report_filename(stock_name: str, ext: str) -> str:
    """Generate a consistent report filename."""
    from datetime import datetime
    safe_name = re.sub(r'[^\w\s-]', '', stock_name).strip().replace(" ", "_")
    return f"{safe_name}_Investor_Report_TAM_{datetime.now().strftime('%Y%m%d')}.{ext}"


SECTION_CONFIG = {
    "fundamental": {
        "prompt_module": "prompts.fundamental_analyst",
        "prompt_var": "FUNDAMENTAL_ANALYSIS_PROMPT",
        "section_key": "fundamental_analysis",
        "title": "Part I: Fundamental Analysis",
    },
    "dividend": {
        "prompt_module": "prompts.dividend_analyst",
        "prompt_var": "DIVIDEND_ANALYSIS_PROMPT",
        "section_key": "dividend_analysis",
        "title": "Dividend Income Analysis",
    },
    "earnings": {
        "prompt_module": "prompts.earnings_analyst",
        "prompt_var": "EARNINGS_ANALYSIS_PROMPT",
        "section_key": "earnings_analysis",
        "title": "Earnings Analysis",
    },
    "risk": {
        "prompt_module": "prompts.risk_analyst",
        "prompt_var": "RISK_ASSESSMENT_PROMPT",
        "section_key": "risk_assessment",
        "title": "Risk Assessment Framework",
    },
    "technical": {
        "prompt_module": "prompts.technical_analyst",
        "prompt_var": "TECHNICAL_ANALYSIS_PROMPT",
        "section_key": "technical_analysis",
        "title": "Technical Analysis Dashboard",
    },
    "sector": {
        "prompt_module": "prompts.sector_rotation",
        "prompt_var": "SECTOR_ROTATION_PROMPT",
        "section_key": "sector_rotation",
        "title": "Sector Rotation Strategy",
    },
    "news": {
        "prompt_module": "prompts.news_impact",
        "prompt_var": "NEWS_IMPACT_PROMPT",
        "section_key": "news_impact",
        "title": "Part II: Recent News Impact Assessment",
    },
    "war": {
        "prompt_module": "prompts.war_impact",
        "prompt_var": "WAR_IMPACT_PROMPT",
        "section_key": "war_impact",
        "title": "Part III: Geopolitical Risk Assessment",
    },
}
