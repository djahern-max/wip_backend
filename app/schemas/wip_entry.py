from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class WIPCreateRequest(BaseModel):
    """Ultra simple WIP creation - just filename and job_number"""

    filename: str
    job_number: str


class WIPUpdateRequest(BaseModel):
    """Update WIP entry fields"""

    job_number: Optional[str] = None
    job_name: Optional[str] = None
    contract_amount: Optional[Decimal] = None
