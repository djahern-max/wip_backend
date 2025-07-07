# app/api/contract_intelligence.py
"""
API endpoints for contract intelligence and document hierarchy
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.api.auth import get_current_active_user
from app.models.user import User
from app.models.contract import Contract
from app.services.contract_intelligence_service import ContractIntelligenceAPI

router = APIRouter()


# Request/Response Models
class ContractIntelligenceRequest(BaseModel):
    contract_ids: List[int]


class DocumentClassification(BaseModel):
    filename: str
    contract_id: Optional[int] = None
    document_type: str
    importance: str
    status: str
    main_parties: List[str]
    contract_value: str
    project_info: str
    confidence: str
    summary: str
    recommendation: str
    importance_score: Optional[int] = None
    is_main_contract: Optional[bool] = False


class ContractIntelligenceResponse(BaseModel):
    main_contract: Optional[DocumentClassification] = None
    supporting_documents: List[DocumentClassification]
    recommendations: dict
    total_contracts: int
    classified_contracts: int
    analysis_date: str


@router.post("/analyze-portfolio", response_model=ContractIntelligenceResponse)
async def analyze_contract_portfolio(
    request: ContractIntelligenceRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Analyze a portfolio of contracts to identify main contract and supporting documents
    """

    if not request.contract_ids:
        raise HTTPException(status_code=400, detail="No contract IDs provided")

    # Verify contracts exist and belong to user (if multi-tenant)
    contracts = db.query(Contract).filter(Contract.id.in_(request.contract_ids)).all()

    if not contracts:
        raise HTTPException(
            status_code=404, detail="No contracts found with provided IDs"
        )

    if len(contracts) != len(request.contract_ids):
        raise HTTPException(status_code=404, detail="Some contract IDs not found")

    try:
        # Analyze portfolio
        intelligence_api = ContractIntelligenceAPI()
        results = intelligence_api.analyze_uploaded_contracts(db, request.contract_ids)

        # Convert to response format
        main_contract = None
        if results.get("main_contract"):
            main_contract = DocumentClassification(**results["main_contract"])

        supporting_documents = [
            DocumentClassification(**doc)
            for doc in results.get("supporting_documents", [])
        ]

        return ContractIntelligenceResponse(
            main_contract=main_contract,
            supporting_documents=supporting_documents,
            recommendations=results.get("recommendations", {}),
            total_contracts=results.get("total_contracts", 0),
            classified_contracts=results.get("classified_contracts", 0),
            analysis_date=results.get("analysis_date", ""),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Portfolio analysis failed: {str(e)}"
        )


@router.get("/contract/{contract_id}/classification")
async def get_contract_classification(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get classification for a single contract
    """

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        intelligence_api = ContractIntelligenceAPI()
        results = intelligence_api.analyze_uploaded_contracts(db, [contract_id])

        # Return the single classification
        if results.get("classifications"):
            classification = results["classifications"][0]
            return DocumentClassification(**classification)
        else:
            raise HTTPException(
                status_code=422, detail="Contract could not be classified"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/auto-identify-main-contract")
async def auto_identify_main_contract(
    request: ContractIntelligenceRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Simple endpoint to identify which contract is the main one
    Returns just the contract ID and confidence
    """

    try:
        intelligence_api = ContractIntelligenceAPI()
        results = intelligence_api.analyze_uploaded_contracts(db, request.contract_ids)

        main_contract = results.get("main_contract")

        if main_contract:
            return {
                "main_contract_id": main_contract.get("contract_id"),
                "filename": main_contract.get("filename"),
                "confidence": main_contract.get("confidence"),
                "importance_score": main_contract.get("importance_score"),
                "document_type": main_contract.get("document_type"),
                "recommendation": "This appears to be the primary contract document",
            }
        else:
            return {
                "main_contract_id": None,
                "recommendation": "Unable to identify a clear main contract",
                "suggestion": "Consider manual review of documents",
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Main contract identification failed: {str(e)}"
        )


@router.get("/recommendations/{contract_id}")
async def get_analysis_recommendations(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get AI recommendations for what to do with a classified contract
    """

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        intelligence_api = ContractIntelligenceAPI()
        results = intelligence_api.analyze_uploaded_contracts(db, [contract_id])

        recommendations = results.get("recommendations", {})

        # Add contract-specific recommendations
        main_contract = results.get("main_contract")
        if main_contract:
            if main_contract.get("recommendation") == "ANALYZE_FULLY":
                recommendations["next_action"] = "full_analysis"
                recommendations["reason"] = (
                    "High-value document suitable for comprehensive analysis"
                )
                recommendations["estimated_cost"] = 0.10
                recommendations["estimated_time"] = "2 minutes"
            elif main_contract.get("recommendation") == "REVIEW_MANUALLY":
                recommendations["next_action"] = "manual_review"
                recommendations["reason"] = (
                    "Document requires human review before processing"
                )
            else:
                recommendations["next_action"] = "archive"
                recommendations["reason"] = "Low priority document"

        return recommendations

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")
