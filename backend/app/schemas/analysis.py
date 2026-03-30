"""Analysis request/response schemas."""

from pydantic import BaseModel


class AnalysisProgress(BaseModel):
    task_id: str
    report_id: str
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    current_step: str
    steps_completed: list[str] = []
    error: str | None = None
