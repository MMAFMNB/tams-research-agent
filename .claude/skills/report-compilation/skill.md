# Report Compilation Skill

## Purpose
Compile all analysis sections into a CIO-level executive summary and full investment report.

## Persona
Chief Investment Officer at TAM Capital.

## Steps
1. Receive all completed analysis sections from Analyst Agent
2. Apply prompt from `prompts/report_compiler.py` (EXECUTIVE_SUMMARY_PROMPT)
3. Call Claude with Sonnet (synthesis requires strong reasoning)
4. Prepend executive summary + key takeaways to full report
5. Add disclaimer: "This document is for informational purposes only..."
6. Pass to generators/ for export (DOCX, PDF, PPTX, XLSX)

## Report Structure (from templates/report_structure.py)
1. Executive Summary + Key Metrics Dashboard
2. Key Takeaways & Investment Thesis (rating, price target, catalysts, risks)
3. Analysis sections in SECTION_ORDER
4. Disclaimer

## Model Selection
- Default: claude-sonnet-4 (CIO-level synthesis)

## Output Formats
- PDF via `generators/pdf_generator.py`
- DOCX via `generators/docx_generator.py`
- PPTX via `generators/pptx_generator.py`
- XLSX via `generators/xlsx_generator.py`
