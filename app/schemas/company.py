# app/schemas/company.py - NEW company schemas
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CompanyBase(BaseModel):
    name: str
    subscription_plan: str = "basic"


class CompanyCreate(CompanyBase):
    pass


class CompanyInDB(CompanyBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class Company(CompanyInDB):
    pass
