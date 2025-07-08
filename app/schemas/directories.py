# app/schemas/directories.py
from typing import List, Optional
from pydantic import BaseModel


# Request Model
class AnalyzeDirectoryRequest(BaseModel):
    directory_path: str


# Response Models
class RankedDocument(BaseModel):
    filename: str
    rank: int
    importance_score: int
    priority_level: str  # MAIN_CONTRACT, HIGH_PRIORITY, etc.
    document_type: str
    importance: str
    status: str
    summary: str
    recommendation: str
    is_main_contract: bool = False
    ranking_reason: Optional[str] = None
    file_path: str
    text_length: int


class DirectoryAnalysisResponse(BaseModel):
    success: bool
    message: str
    job_name: str
    job_number: str

    # Main results - exactly like your script
    main_contract: Optional[RankedDocument] = None
    ranked_documents: List[RankedDocument]

    # Summary stats - exactly like your script
    total_documents: int
    successful_scans: int
    failed_scans: int
    success_rate: float

    # Classification breakdown - exactly like your script
    critical_documents: int
    primary_contracts: int
    executed_documents: int
    recommended_for_analysis: int

    # Cost estimates - exactly like your script
    estimated_scan_cost: float
    estimated_analysis_cost: float
    estimated_analysis_time_minutes: int

    # Recommendations - exactly like your script
    recommended_files: List[str]
    failed_files: List[str]
