"""Base analyst class for all analysis modules."""

import anthropic
from app.config import get_settings

settings = get_settings()


def call_claude(prompt: str, locale: str = "en") -> str:
    """Call Claude API with locale-aware instructions."""
    if locale == "ar":
        prompt = (
            "IMPORTANT: Write your entire analysis in Arabic (العربية). "
            "Use Arabic numerals where appropriate. Structure all headings in Arabic. "
            "Maintain the same analytical rigor and structure.\n\n"
            + prompt
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


SECTION_CONFIG = {
    "fundamental": {
        "module": "app.analysis.fundamental",
        "prompt_var": "FUNDAMENTAL_ANALYSIS_PROMPT",
        "section_key": "fundamental_analysis",
        "title": "Part I: Fundamental Analysis",
        "title_ar": "الجزء الأول: التحليل الأساسي",
        "sort_order": 1,
    },
    "dividend": {
        "module": "app.analysis.dividend",
        "prompt_var": "DIVIDEND_ANALYSIS_PROMPT",
        "section_key": "dividend_analysis",
        "title": "Dividend Income Analysis",
        "title_ar": "تحليل دخل التوزيعات",
        "sort_order": 2,
    },
    "earnings": {
        "module": "app.analysis.earnings",
        "prompt_var": "EARNINGS_ANALYSIS_PROMPT",
        "section_key": "earnings_analysis",
        "title": "Earnings Analysis",
        "title_ar": "تحليل الأرباح",
        "sort_order": 3,
    },
    "risk": {
        "module": "app.analysis.risk",
        "prompt_var": "RISK_ASSESSMENT_PROMPT",
        "section_key": "risk_assessment",
        "title": "Risk Assessment Framework",
        "title_ar": "إطار تقييم المخاطر",
        "sort_order": 4,
    },
    "technical": {
        "module": "app.analysis.technical",
        "prompt_var": "TECHNICAL_ANALYSIS_PROMPT",
        "section_key": "technical_analysis",
        "title": "Technical Analysis Dashboard",
        "title_ar": "لوحة التحليل الفني",
        "sort_order": 5,
    },
    "sector": {
        "module": "app.analysis.sector_rotation",
        "prompt_var": "SECTOR_ROTATION_PROMPT",
        "section_key": "sector_rotation",
        "title": "Sector Rotation Strategy",
        "title_ar": "استراتيجية دوران القطاعات",
        "sort_order": 6,
    },
    "news": {
        "module": "app.analysis.news_impact",
        "prompt_var": "NEWS_IMPACT_PROMPT",
        "section_key": "news_impact",
        "title": "Part II: Recent News Impact Assessment",
        "title_ar": "الجزء الثاني: تقييم تأثير الأخبار",
        "sort_order": 7,
    },
    "war": {
        "module": "app.analysis.war_impact",
        "prompt_var": "WAR_IMPACT_PROMPT",
        "section_key": "war_impact",
        "title": "Part III: Geopolitical Risk Assessment",
        "title_ar": "الجزء الثالث: تقييم المخاطر الجيوسياسية",
        "sort_order": 8,
    },
    "esg": {
        "module": "app.analysis.esg",
        "prompt_var": "ESG_ANALYSIS_PROMPT",
        "section_key": "esg_analysis",
        "title": "ESG & Sustainability Analysis",
        "title_ar": "تحليل الحوكمة البيئية والاجتماعية",
        "sort_order": 9,
    },
    "peer": {
        "module": "app.analysis.peer_comparison",
        "prompt_var": "PEER_COMPARISON_PROMPT",
        "section_key": "peer_comparison",
        "title": "Peer Comparison Analysis",
        "title_ar": "تحليل مقارنة الأقران",
        "sort_order": 10,
    },
    "insider": {
        "module": "app.analysis.insider_activity",
        "prompt_var": "INSIDER_ACTIVITY_PROMPT",
        "section_key": "insider_activity",
        "title": "Insider Activity Analysis",
        "title_ar": "تحليل نشاط المطلعين",
        "sort_order": 11,
    },
}


def get_analysis_sections_from_request(user_message: str) -> list[str]:
    """Determine which analysis sections to generate based on user request."""
    message = user_message.lower()

    if any(kw in message for kw in ["full report", "comprehensive", "complete analysis",
                                     "investor report", "كامل", "تقرير شامل"]):
        return list(SECTION_CONFIG.keys())

    sections = []
    keyword_map = {
        "fundamental": ["fundamental", "أساسي", "goldman", "valuation", "business model"],
        "technical": ["technical", "فني", "chart", "morgan stanley", "شارت", "support", "resistance"],
        "earnings": ["earnings", "أرباح", "eps", "jpmorgan", "whisper"],
        "dividend": ["dividend", "توزيعات", "income", "yield", "عائد"],
        "risk": ["risk", "مخاطر", "stress test"],
        "sector": ["sector", "rotation", "قطاع", "macro"],
        "news": ["news", "أخبار", "impact", "recent"],
        "war": ["war", "geopolitical", "حرب", "conflict", "hormuz"],
        "esg": ["esg", "sustainability", "استدامة", "governance", "حوكمة"],
        "peer": ["peer", "comparison", "مقارنة", "competitors"],
        "insider": ["insider", "مطلعين", "ownership", "ملكية"],
    }

    for section, keywords in keyword_map.items():
        if any(kw in message for kw in keywords):
            sections.append(section)

    # Default to full analysis
    if not sections:
        sections = ["fundamental", "dividend", "earnings", "risk", "technical", "sector", "news"]

    return sections
