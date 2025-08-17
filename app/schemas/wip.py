# ===== backend/app/schemas/wip.py =====
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WIPBase(BaseModel):
    job_number: str
    project_name: str


class WIPCreate(WIPBase):
    pass


class WIPUpdate(BaseModel):
    job_number: Optional[str] = None
    project_name: Optional[str] = None


class WIPInDBBase(WIPBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WIP(WIPInDBBase):
    pass


class WIPInDB(WIPInDBBase):
    pass
