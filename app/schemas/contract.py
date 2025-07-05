from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ContractBase(BaseModel):
    contract_number: Optional[str] = None
    contract_name: Optional[str] = None
    contract_value: Optional[Decimal] = None


class ContractCreate(ContractBase):
    filename: str
    raw_text: Optional[str] = None


class ContractInDB(ContractBase):
    id: int
    filename: str
    raw_text: Optional[str]
    is_processed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Contract(ContractInDB):
    pass


class ContractUploadResponse(BaseModel):
    message: str
    contract_id: int
    extracted_data: Contract
