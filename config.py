import os
from dotenv import load_dotenv

# Load .env from the project directory (not CWD) — used for local dev
_project_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_project_dir, ".env"), override=True)

# Support both .env (local) and Streamlit secrets (cloud deployment)
def _get_secret(key, default=""):
    """Read from Streamlit secrets first, then environment variables."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
TWELVE_DATA_API_KEY = _get_secret("TWELVE_DATA_API_KEY")
MODEL = "claude-sonnet-4-20250514"
FALLBACK_MODEL = "claude-haiku-3-5-20241022"

# TAMS branding colors (from TAM Capital Brand Guidelines)
TAMS_DEEP_BLUE = "#222F62"      # Primary
TAMS_LIGHT_BLUE = "#1A6DB6"     # Secondary - accent
TAMS_TURQUOISE = "#6CB9B6"      # Secondary - highlights
TAMS_SOFT_CARBON = "#B1B3B6"    # Neutral
TAMS_DARK_CARBON = "#0E1A24"    # Dark backgrounds
TAMS_WHITE = "#FFFFFF"

# Legacy aliases (used in existing code, mapped to new brand colors)
TAMS_DARK_BLUE = TAMS_DEEP_BLUE
TAMS_GREEN = TAMS_LIGHT_BLUE    # Replaced green with brand light blue
TAMS_GRAY = "#4A4A4A"           # Body text gray (not in guidelines but needed)
TAMS_LIGHT_BLUE_BG = "#E8F0F8"  # Light background for table rows

# File paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TAMS_LOGO = os.path.join(ASSETS_DIR, "tams_logo.png")
TAMS_FOOTER = os.path.join(ASSETS_DIR, "tams_footer.png")
TAMS_BG = os.path.join(ASSETS_DIR, "tams_bg.png")
TAMS_PPTX_TEMPLATE = os.path.join(ASSETS_DIR, "tam_template.pptx")
TAMS_PPTX_TEMPLATE_AR = os.path.join(ASSETS_DIR, "tam_template_ar.pptx")

# Tadawul ticker mapping (common Saudi stocks)
TADAWUL_TICKERS = {
    "2020": "2020.SR",  # SABIC Agri-Nutrients
    "2010": "2010.SR",  # SABIC
    "2222": "2222.SR",  # Saudi Aramco
    "1120": "1120.SR",  # Al Rajhi Bank
    "7010": "7010.SR",  # STC
    "2350": "2350.SR",  # Saudi Kayan
    "1180": "1180.SR",  # Al Inma Bank
    "2280": "2280.SR",  # Almarai
    "2060": "2060.SR",  # National Industrialization
    "4030": "4030.SR",  # Bahri
    "1010": "1010.SR",  # Riyad Bank
    "1150": "1150.SR",  # Alinma Bank
    "3060": "3060.SR",  # United Electronics
    "4200": "4200.SR",  # Aldawaa
    "4001": "4001.SR",  # Petromin
}


def resolve_ticker(user_input: str) -> str:
    """Resolve user input to a Yahoo Finance ticker symbol."""
    cleaned = user_input.strip().upper()

    # Direct Tadawul number
    if cleaned in TADAWUL_TICKERS:
        return TADAWUL_TICKERS[cleaned]

    # Already has .SR suffix
    if cleaned.endswith(".SR"):
        return cleaned

    # Try adding .SR for pure numbers
    if cleaned.isdigit():
        return f"{cleaned}.SR"

    # Assume it's a global ticker (e.g., AAPL, MSFT)
    return cleaned
