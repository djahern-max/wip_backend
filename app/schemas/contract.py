# app/schemas/contract.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


# =============================================================================
# CONTRACT SCHEMAS (Simplified - just storage)
# =============================================================================


class ContractBase(BaseModel):
    filename: str
    job_number: Optional[str] = None
    job_name: Optional[str] = None


class ContractCreate(ContractBase):
    raw_text: Optional[str] = None
    company_id: Optional[int] = None


class ContractInDB(ContractBase):
    id: int
    raw_text: Optional[str]
    is_processed: bool
    created_at: datetime
    company_id: Optional[int] = None

    class Config:
        from_attributes = True


class Contract(ContractInDB):
    pass


# =============================================================================
# CONTRACT ANALYSIS SCHEMAS (AI-extracted data)
# =============================================================================


class ContractAnalysisBase(BaseModel):
    contract_number: Optional[str] = None
    contract_name: Optional[str] = None
    contract_value: Optional[Decimal] = None
    contractor_name: Optional[str] = None
    subcontractor_name: Optional[str] = None
    owner_name: Optional[str] = None
    project_location: Optional[str] = None
    work_description: Optional[str] = None
    project_type: Optional[str] = None
    payment_terms: Optional[str] = None
    retainage_percentage: Optional[Decimal] = None
    insurance_required: bool = False
    bond_required: bool = False
    insurance_amount: Optional[Decimal] = None
    bond_amount: Optional[Decimal] = None


class ContractAnalysisCreate(ContractAnalysisBase):
    contract_id: int
    agreement_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ai_provider: str = "claude-3-sonnet"
    confidence_score: Optional[Decimal] = None


class ContractAnalysisInDB(ContractAnalysisBase):
    id: int
    contract_id: int
    agreement_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ai_provider: str
    analysis_date: datetime
    confidence_score: Optional[Decimal] = None

    class Config:
        from_attributes = True


class ContractAnalysis(ContractAnalysisInDB):
    pass


# =============================================================================
# COMBINED SCHEMAS (Contract + Analysis)
# =============================================================================


class ContractWithAnalysis(Contract):
    """Contract with optional analysis data"""

    analysis: Optional[ContractAnalysis] = None


class ContractListItem(BaseModel):
    """Simplified contract info for list endpoints"""

    id: int
    filename: str
    created_at: datetime
    is_processed: bool
    is_analyzed: bool
    text_length: int

    # Analysis summary (if available)
    analysis_id: Optional[int] = None
    contract_number: Optional[str] = None
    contract_name: Optional[str] = None
    contract_value: Optional[str] = None  # String for API responses
    contractor_name: Optional[str] = None
    subcontractor_name: Optional[str] = None
    analysis_date: Optional[datetime] = None
    ai_provider: Optional[str] = None


# =============================================================================
# API RESPONSE SCHEMAS
# =============================================================================


class ContractUploadResponse(BaseModel):
    """Response for text extraction endpoint"""

    message: str
    contract_id: int
    text_length: int
    preview: str


class ContractAnalysisResponse(BaseModel):
    """Response for analysis endpoint"""

    message: str
    contract_id: int
    analysis_id: int
    extracted_data: dict  # Flexible dict for now
    analysis_provider: str
    fields_extracted: Optional[int] = None
    total_possible_fields: Optional[int] = None
    text_length: Optional[int] = None


class ContractListResponse(BaseModel):
    """Response for list endpoint"""

    contracts: list[ContractListItem]
    total_count: int


class ContractDetailResponse(BaseModel):
    """Response for detailed contract view"""

    id: int
    filename: str
    created_at: datetime
    is_processed: bool
    text_length: int
    raw_text_preview: Optional[str]
    analysis: Optional[dict] = None  # Full analysis data if available


# =============================================================================
# ERROR SCHEMAS
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response"""

    detail: str
    error_code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response"""

    detail: str
    field_errors: Optional[dict] = None
