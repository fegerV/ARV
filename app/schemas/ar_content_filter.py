from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ARContentFilter(BaseModel):
    search: Optional[str] = None
    company_id: Optional[int] = None
    project_id: Optional[int] = None
    marker_status: Optional[str] = None
    is_active: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None