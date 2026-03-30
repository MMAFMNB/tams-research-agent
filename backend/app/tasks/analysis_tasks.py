"""Celery tasks for running analysis pipeline."""

import importlib
import re
import os
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.config import get_settings
from app.analysis.base import call_claude, SECTION_CONFIG
from app.analysis.compiler import EXECUTIVE_SUMMARY_PROMPT
from app.data.source_collector import SourceCollector

settings = get_settings()


@celery_app.task(bind=True, name="analysis.run_full")
def run_full_analysis_task(self, report_id: str, ticker: str, company_name: str,
                            sections: list[str], locale: str, formats: list[str]):
    """Run the full analysis pipeline as a background task."""
    from app.core.database import async_session_factory
    from app.models.report import Report, ReportStatus
    from app.models.report_section import ReportSection
    from app.models.report_snapshot import ReportSnapshot
    from app.models.report_source import ReportSource
    from app.models.report_file import ReportFile, FileType
    import asyncio

    collector = SourceCollector()

    def update_progress(progress: int, step: str):
        self.update_state(state="PROGRESS", meta={
            "report_id": report_id,
            "progress": progress,
            "current_step": step,
        })

    try:
        # Step 1: Fetch market data (10%)
        update_progress(5, "Fetching market data...")
        from app.data.yahoo_finance import (
            fetch_stock_data, fetch_price_history, fetch_financials,
            fetch_dividend_history, calculate_technical_indicators,
            format_market_data_for_prompt
        )

        stock_data = fetch_stock_data(ticker)
        collector.add("yahoo_finance", f"Yahoo Finance - {stock_data.get('name', ticker)} Quote",
                      f"https://finance.yahoo.com/quote/{ticker}",
                      "Live stock price and valuation metrics",
                      delay_minutes=15)

        if stock_data.get("name") and stock_data["name"] != ticker:
            company_name = stock_data["name"]

        update_progress(8, "Loading price history...")
        hist = fetch_price_history(ticker)
        collector.add("yahoo_finance", f"Yahoo Finance - {ticker} Historical Prices",
                      f"https://finance.yahoo.com/quote/{ticker}/history/",
                      "OHLCV price data, 2y period", delay_minutes=15)

        technicals = calculate_technical_indicators(hist) if not hist.empty else {}

        update_progress(10, "Scanning news...")
        from app.data.news_search import search_company_news
        news = search_company_news(company_name, ticker)
        # Add news sources
        collector.add("web_search", f"News search for {company_name}",
                      description="DuckDuckGo news aggregation")

        financials = fetch_financials(ticker)
        collector.add("financial_statements", f"Yahoo Finance - {ticker} Financial Statements",
                      f"https://finance.yahoo.com/quote/{ticker}/financials/",
                      "Income statement, balance sheet, cash flow", delay_minutes=15)

        dividends = fetch_dividend_history(ticker)

        market_data_str = format_market_data_for_prompt(stock_data, technicals, hist)

        # Step 2: Generate charts (15%)
        update_progress(15, "Generating charts...")
        from app.generators.chart_generator import generate_all_charts
        chart_dir = os.path.join(settings.LOCAL_STORAGE_PATH, "charts", report_id)
        os.makedirs(chart_dir, exist_ok=True)
        charts = generate_all_charts(stock_data, technicals, hist, financials, dividends, chart_dir)

        # Step 3: Determine sections to analyze
        if not sections:
            sections = list(SECTION_CONFIG.keys())

        # Step 4: Run AI analysis (20-85%)
        total_sections = len(sections)
        results = {}

        for i, section_type in enumerate(sections):
            config = SECTION_CONFIG.get(section_type)
            if not config:
                continue

            progress = 20 + int((i / total_sections) * 65)
            title = config.get(f"title_{'ar' if locale == 'ar' else ''}", config["title"])
            update_progress(progress, f"[{i+1}/{total_sections}] {title}")

            try:
                module = importlib.import_module(config["module"])
                prompt_template = getattr(module, config["prompt_var"])
                prompt = prompt_template.format(market_data=market_data_str, news_data=news)
                content = call_claude(prompt, locale=locale)
                results[config["section_key"]] = {
                    "content": content,
                    "title": title,
                    "sort_order": config["sort_order"],
                }
            except Exception as e:
                results[config["section_key"]] = {
                    "content": f"Error generating section: {str(e)}",
                    "title": title,
                    "sort_order": config["sort_order"],
                }

        # Step 5: Executive Summary (88%)
        update_progress(88, "Compiling executive summary...")
        if results:
            all_sections_text = "\n\n---\n\n".join(
                f"[{k}]\n{v['content']}" for k, v in results.items()
            )
            exec_prompt = EXECUTIVE_SUMMARY_PROMPT.format(
                market_data=market_data_str,
                all_sections=all_sections_text[:8000]
            )
            exec_summary = call_claude(exec_prompt, locale=locale)

            if "KEY TAKEAWAYS" in exec_summary.upper():
                parts = re.split(r'(?i)key\s*takeaways', exec_summary, maxsplit=1)
                results["executive_summary"] = {
                    "content": parts[0].strip(),
                    "title": "Executive Summary" if locale == "en" else "الملخص التنفيذي",
                    "sort_order": 0,
                }
                results["key_takeaways"] = {
                    "content": "Key Takeaways" + parts[1] if len(parts) > 1 else "",
                    "title": "Key Takeaways" if locale == "en" else "النتائج الرئيسية",
                    "sort_order": 99,
                }
            else:
                results["executive_summary"] = {
                    "content": exec_summary,
                    "title": "Executive Summary" if locale == "en" else "الملخص التنفيذي",
                    "sort_order": 0,
                }

        # Step 6: Generate documents (90-98%)
        update_progress(90, "Generating documents...")
        output_dir = os.path.join(settings.LOCAL_STORAGE_PATH, "reports", report_id)
        os.makedirs(output_dir, exist_ok=True)

        sections_content = {k: v["content"] for k, v in results.items()}
        generated_files = {}

        if "docx" in formats:
            update_progress(92, "Creating Word document...")
            from app.generators.docx_generator import generate_docx_report
            try:
                docx_path = generate_docx_report(
                    company_name, ticker, sections_content,
                    charts=charts, output_dir=output_dir, sources=collector
                )
                generated_files["docx"] = docx_path
            except Exception:
                pass

        if "pdf" in formats:
            update_progress(94, "Creating PDF...")
            from app.generators.pdf_generator import convert_docx_to_pdf
            docx_for_pdf = generated_files.get("docx")
            if not docx_for_pdf and "docx" not in formats:
                from app.generators.docx_generator import generate_docx_report
                try:
                    docx_for_pdf = generate_docx_report(
                        company_name, ticker, sections_content,
                        charts=charts, output_dir=output_dir, sources=collector
                    )
                except Exception:
                    pass
            if docx_for_pdf:
                try:
                    pdf_path = convert_docx_to_pdf(docx_for_pdf)
                    generated_files["pdf"] = pdf_path
                except Exception:
                    pass

        if "pptx" in formats:
            update_progress(96, "Creating PowerPoint...")
            from app.generators.pptx_generator import generate_pptx_report
            try:
                pptx_path = generate_pptx_report(
                    company_name, ticker, sections_content,
                    charts=charts, output_dir=output_dir, sources=collector
                )
                generated_files["pptx"] = pptx_path
            except Exception:
                pass

        # Step 7: Save to database (98%)
        update_progress(98, "Saving results...")

        async def save_to_db():
            async with async_session_factory() as session:
                # Update report status
                from sqlalchemy import select
                result = await session.execute(select(Report).where(Report.id == report_id))
                report = result.scalar_one()
                report.status = ReportStatus.COMPLETED
                report.completed_at = datetime.now(timezone.utc)
                report.company_name = company_name

                # Save sections
                for key, data in results.items():
                    section = ReportSection(
                        report_id=report_id,
                        section_key=key,
                        title=data["title"],
                        content=data["content"],
                        sort_order=data["sort_order"],
                    )
                    session.add(section)

                # Save snapshot
                snapshot = ReportSnapshot(
                    report_id=report_id,
                    current_price=stock_data.get("current_price"),
                    market_cap=stock_data.get("market_cap"),
                    pe_ratio=stock_data.get("pe_ratio"),
                    forward_pe=stock_data.get("forward_pe"),
                    eps_ttm=stock_data.get("eps_ttm"),
                    dividend_yield=stock_data.get("dividend_yield"),
                    raw_market_data=stock_data,
                )
                session.add(snapshot)

                # Save sources
                for src in collector.sources:
                    source = ReportSource(
                        report_id=report_id,
                        source_type=src.source_type,
                        title=src.title,
                        url=src.url,
                        accessed_at=src.accessed_at,
                        reliability=src.reliability,
                        is_realtime=src.is_realtime,
                        delay_minutes=src.delay_minutes,
                        description=src.description,
                    )
                    session.add(source)

                # Save files
                for fmt, path in generated_files.items():
                    file_size = os.path.getsize(path) if os.path.exists(path) else 0
                    rf = ReportFile(
                        report_id=report_id,
                        file_type=fmt,
                        storage_path=path,
                        file_size=file_size,
                    )
                    session.add(rf)

                await session.commit()

        asyncio.run(save_to_db())

        update_progress(100, "Complete")
        return {"report_id": report_id, "status": "completed", "files": generated_files}

    except Exception as e:
        # Mark report as failed
        async def mark_failed():
            async with async_session_factory() as session:
                from sqlalchemy import select
                result = await session.execute(select(Report).where(Report.id == report_id))
                report = result.scalar_one_or_none()
                if report:
                    report.status = ReportStatus.FAILED
                    await session.commit()

        import asyncio
        asyncio.run(mark_failed())
        raise
