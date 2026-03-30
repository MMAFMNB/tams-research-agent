"""Reports API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.models.report import Report
from app.models.report_snapshot import ReportSnapshot
from app.schemas.report import ReportResponse, ReportDetailResponse, ReportComparisonResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    ticker: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    """List reports, optionally filtered by ticker."""
    query = select(Report).order_by(desc(Report.created_at))
    if ticker:
        query = query.where(Report.ticker == ticker)
    if user:
        query = query.where(Report.user_id == user.id)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full report with sections, files, sources, and snapshot."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Eagerly load relationships
    await db.refresh(report, ["sections", "files", "sources", "snapshot"])
    return report


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    await db.delete(report)
    return {"status": "deleted"}


@router.get("/compare/{ticker}")
async def compare_reports(
    ticker: str,
    report_ids: str = Query(default="", description="Comma-separated report IDs"),
    db: AsyncSession = Depends(get_db),
):
    """Compare reports for the same ticker over time."""
    query = select(Report).where(Report.ticker == ticker).order_by(desc(Report.created_at))
    if report_ids:
        ids = [rid.strip() for rid in report_ids.split(",") if rid.strip()]
        if ids:
            query = query.where(Report.id.in_(ids))
    query = query.limit(10)
    result = await db.execute(query)
    reports = result.scalars().all()

    if len(reports) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 reports to compare")

    # Load snapshots
    snapshots = []
    for report in reports:
        snap_result = await db.execute(
            select(ReportSnapshot).where(ReportSnapshot.report_id == report.id)
        )
        snap = snap_result.scalar_one_or_none()
        if snap:
            snapshots.append(snap)

    # Compute changes between most recent and previous
    changes = {}
    if len(snapshots) >= 2:
        latest = snapshots[0]
        previous = snapshots[1]

        if latest.price_target and previous.price_target:
            changes["price_target_change"] = float(latest.price_target) - float(previous.price_target)
        if latest.rating != previous.rating:
            changes["rating_change"] = {"from": previous.rating, "to": latest.rating}
        if latest.current_price and previous.current_price:
            changes["price_change"] = float(latest.current_price) - float(previous.current_price)

        # Compare risks
        latest_risks = set((latest.key_risks or {}).get("items", []))
        previous_risks = set((previous.key_risks or {}).get("items", []))
        changes["new_risks"] = list(latest_risks - previous_risks)
        changes["removed_risks"] = list(previous_risks - latest_risks)

    return {
        "ticker": ticker,
        "reports": reports,
        "snapshots": snapshots,
        "changes": changes,
    }


@router.get("/history/{ticker}", response_model=list[ReportResponse])
async def report_history(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """Get chronological list of reports for a ticker."""
    result = await db.execute(
        select(Report)
        .where(Report.ticker == ticker)
        .order_by(desc(Report.created_at))
        .limit(50)
    )
    return result.scalars().all()
