"""Export and sharing API endpoints."""

import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.report import Report
from app.models.report_file import ReportFile
from app.models.share_link import ShareLink
from app.schemas.report import ShareLinkCreate, ShareLinkResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/reports/{report_id}/files")
async def list_report_files(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List available files for a report."""
    result = await db.execute(
        select(ReportFile).where(ReportFile.report_id == report_id)
    )
    return result.scalars().all()


@router.get("/reports/{report_id}/files/{file_id}/download")
async def download_file(
    report_id: str,
    file_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a report file."""
    result = await db.execute(
        select(ReportFile).where(ReportFile.id == file_id, ReportFile.report_id == report_id)
    )
    report_file = result.scalar_one_or_none()
    if not report_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(
        path=report_file.storage_path,
        filename=report_file.storage_path.split("/")[-1],
        media_type="application/octet-stream",
    )


@router.post("/reports/{report_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    report_id: str,
    request: ShareLinkCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a shareable link for a report."""
    # Verify report exists
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    expires_at = None
    if request.expires_in_hours:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=request.expires_in_hours)

    share = ShareLink(
        report_id=report_id,
        file_type=request.file_type,
        expires_at=expires_at,
    )
    db.add(share)
    await db.flush()
    await db.refresh(share)

    return ShareLinkResponse(
        share_url=f"/share/{share.token}",
        token=share.token,
        expires_at=share.expires_at,
    )


@router.get("/share/{token}")
async def access_shared_report(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Access a shared report via token (public, no auth)."""
    result = await db.execute(select(ShareLink).where(ShareLink.token == token))
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    # Check expiry
    if share.expires_at and datetime.now(timezone.utc) > share.expires_at:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link expired")

    # Check access limit
    if share.max_access and share.access_count >= share.max_access:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Access limit reached")

    # Increment counter
    share.access_count += 1

    # Get the file
    file_result = await db.execute(
        select(ReportFile)
        .where(ReportFile.report_id == share.report_id)
        .where(ReportFile.file_type == share.file_type)
    )
    report_file = file_result.scalar_one_or_none()
    if not report_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(
        path=report_file.storage_path,
        filename=report_file.storage_path.split("/")[-1],
        media_type="application/octet-stream",
    )
