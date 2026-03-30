"""Analysis API endpoints - triggers report generation."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.config import get_settings
from app.models.report import Report, ReportStatus
from app.schemas.report import AnalysisRequest, AnalysisStatusResponse

router = APIRouter()
settings = get_settings()


@router.post("/run", response_model=AnalysisStatusResponse)
async def run_analysis(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new analysis. Returns task_id for progress tracking."""
    # Resolve ticker
    ticker = settings.resolve_ticker(request.ticker)
    company_name = request.company_name or ticker

    # Create report record
    report = Report(
        ticker=ticker,
        company_name=company_name,
        locale=request.locale,
        status=ReportStatus.PENDING,
        report_type="full" if not request.sections else "partial",
        chat_session_id=request.chat_session_id,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    # Dispatch Celery task
    from app.tasks.analysis_tasks import run_full_analysis_task
    task = run_full_analysis_task.delay(
        report_id=report.id,
        ticker=ticker,
        company_name=company_name,
        sections=request.sections or [],
        locale=request.locale,
        formats=request.formats,
    )

    report.status = ReportStatus.RUNNING
    await db.flush()

    return AnalysisStatusResponse(
        task_id=task.id,
        report_id=report.id,
        status="running",
        progress=0,
        current_step="Initializing analysis...",
    )


@router.get("/{task_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    """Check the status of a running analysis task."""
    from app.tasks.analysis_tasks import run_full_analysis_task
    result = run_full_analysis_task.AsyncResult(task_id)

    if result.state == "PENDING":
        return AnalysisStatusResponse(
            task_id=task_id, report_id="", status="pending", progress=0, current_step="Queued..."
        )
    elif result.state == "PROGRESS":
        info = result.info or {}
        return AnalysisStatusResponse(
            task_id=task_id,
            report_id=info.get("report_id", ""),
            status="running",
            progress=info.get("progress", 0),
            current_step=info.get("current_step", "Processing..."),
        )
    elif result.state == "SUCCESS":
        info = result.result or {}
        return AnalysisStatusResponse(
            task_id=task_id,
            report_id=info.get("report_id", ""),
            status="completed",
            progress=100,
            current_step="Complete",
        )
    else:
        return AnalysisStatusResponse(
            task_id=task_id, report_id="", status="failed", progress=0,
            current_step=str(result.info) if result.info else "Unknown error",
        )
