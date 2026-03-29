"""Convert DOCX to PDF."""

import os
import subprocess
import sys


def convert_docx_to_pdf(docx_path: str) -> str:
    """Convert a DOCX file to PDF.

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
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, docx_path],
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
