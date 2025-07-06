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


# app/schemas/user.py - Updated user schemas
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    company_id: Optional[int] = None  # Optional for MVP


class UserUpdate(UserBase):
    password: Optional[str] = None
    company_id: Optional[int] = None


class UserInDB(UserBase):
    id: int
    is_superuser: bool
    company_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class User(UserInDB):
    pass


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# app/schemas/contract.py - Updated contract schemas
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


# =============================================================================
# CONTRACT SCHEMAS with Company and Job Support
# =============================================================================


class ContractBase(BaseModel):
    filename: str
    job_number: Optional[str] = None  # NEW: Optional job number
    job_name: Optional[str] = None  # NEW: Optional job name


class ContractCreate(ContractBase):
    raw_text: Optional[str] = None
    company_id: Optional[int] = None  # NEW: Company association


class ContractInDB(ContractBase):
    id: int
    raw_text: Optional[str]
    is_processed: bool
    company_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Contract(ContractInDB):
    # NEW: Computed properties for display
    display_job_identifier: Optional[str] = None
    display_job_name: Optional[str] = None


# =============================================================================
# CONTRACT ANALYSIS SCHEMAS (Updated)
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
    company_id: Optional[int] = None  # NEW: Company association
    agreement_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    ai_provider: str = "claude-3-sonnet"
    confidence_score: Optional[Decimal] = None


class ContractAnalysisInDB(ContractAnalysisBase):
    id: int
    contract_id: int
    company_id: Optional[int] = None
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
# ENHANCED RESPONSE SCHEMAS
# =============================================================================


class ContractListItem(BaseModel):
    """Enhanced contract info for list endpoints with job grouping"""

    id: int
    filename: str
    created_at: datetime
    is_processed: bool
    is_analyzed: bool
    text_length: int

    # NEW: Job and company information
    job_number: Optional[str] = None
    job_name: Optional[str] = None
    display_job_identifier: Optional[str] = None
    display_job_name: Optional[str] = None
    company_id: Optional[int] = None

    # Analysis summary (if available)
    analysis_id: Optional[int] = None
    contract_number: Optional[str] = None
    contract_name: Optional[str] = None
    contract_value: Optional[str] = None
    contractor_name: Optional[str] = None
    subcontractor_name: Optional[str] = None
    analysis_date: Optional[datetime] = None
    ai_provider: Optional[str] = None


class JobGroupedContracts(BaseModel):
    """NEW: Grouped contracts by job for future job management"""

    job_identifier: str  # job_number or auto-generated
    job_name: Optional[str] = None
    contracts: list[ContractListItem]
    total_contracts: int
    analyzed_contracts: int
    total_value: Optional[Decimal] = None


class ContractUploadResponse(BaseModel):
    """Enhanced upload response with job information"""

    message: str
    contract_id: int
    text_length: int
    preview: str

    # NEW: Job information
    job_number: Optional[str] = None
    job_name: Optional[str] = None
    display_job_identifier: str
    security_status: str = "ENCRYPTED"


class ContractListResponse(BaseModel):
    """Enhanced list response with job grouping option"""

    contracts: list[ContractListItem]
    total_count: int

    # NEW: Optional job grouping
    grouped_by_jobs: Optional[list[JobGroupedContracts]] = None
    unique_jobs: Optional[int] = None

    security_status: str = "ALL_DATA_ENCRYPTED"


# =============================================================================
# COMPANY RESPONSE SCHEMAS
# =============================================================================


class CompanyWithStats(BaseModel):
    """Company information with usage statistics"""

    id: int
    name: str
    subscription_plan: str
    is_active: bool
    created_at: datetime

    # Statistics
    total_contracts: int = 0
    analyzed_contracts: int = 0
    total_users: int = 0
    unique_jobs: int = 0
