from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class ReportImageResponse(BaseModel):
    id: UUID
    report_id: UUID
    file_path: str
    thumbnail_path: Optional[str] = None
    file_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
