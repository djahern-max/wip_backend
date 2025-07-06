from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis
from app.api.auth import get_current_active_user
from app.models.user import User
from app.services.claude_contract_analyzer import ComprehensiveClaudeAnalyzer
from app.schemas.contract import (
    ContractAnalysisResponse,
    ContractListResponse,
    ContractDetailResponse,
)

router = APIRouter()


@router.post("/extract-text")
async def extract_contract_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Extract text from PDF and store in contracts table"""

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        # Read file content
        file_content = await file.read()

        # Extract text from PDF using Google Cloud Vision
        from app.services.pdf_extractor import extract_text_from_uploaded_file

        raw_text = extract_text_from_uploaded_file(file_content)

        if not raw_text:
            raise HTTPException(
                status_code=422, detail="Failed to extract text from PDF."
            )

        # Save to simplified contracts table
        db_contract = Contract(
            filename=file.filename,
            raw_text=raw_text,
            is_processed=True,
        )

        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)

        return {
            "message": "Text extracted successfully",
            "contract_id": db_contract.id,
            "text_length": len(raw_text),
            "preview": raw_text[:200] + "..." if len(raw_text) > 200 else raw_text,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")


@router.post("/analyze/{contract_id}", response_model=ContractAnalysisResponse)
async def analyze_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Analyze contract using Claude AI and store results in contract_analyses table
    """

    # Get contract from database
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if not contract.raw_text:
        raise HTTPException(
            status_code=422, detail="No text found - extract text first"
        )

    # Check if already analyzed
    existing_analysis = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract_id)
        .first()
    )

    if existing_analysis:
        return {
            "message": "Contract already analyzed",
            "contract_id": contract.id,
            "analysis_id": existing_analysis.id,
            "extracted_data": {
                "contract_number": existing_analysis.contract_number,
                "contract_name": existing_analysis.contract_name,
                "contract_value": (
                    str(existing_analysis.contract_value)
                    if existing_analysis.contract_value
                    else None
                ),
                "contractor_name": existing_analysis.contractor_name,
                "subcontractor_name": existing_analysis.subcontractor_name,
                "project_location": existing_analysis.project_location,
                "agreement_date": (
                    existing_analysis.agreement_date.isoformat()
                    if existing_analysis.agreement_date
                    else None
                ),
            },
            "analysis_provider": existing_analysis.ai_provider,
            "analysis_date": existing_analysis.analysis_date.isoformat(),
        }

    try:
        # Initialize Claude analyzer
        analyzer = ComprehensiveClaudeAnalyzer()

        # Analyze the contract
        analysis_result = analyzer.analyze_contract(contract.raw_text)

        if not analysis_result["success"]:
            raise HTTPException(status_code=500, detail="Contract analysis failed")

        # Extract the data from the nested structure
        extracted_data = analysis_result["data"]

        # Create new analysis record
        db_analysis = ContractAnalysis(
            contract_id=contract_id,
            contract_number=extracted_data.get("contract_number"),
            contract_name=extracted_data.get("contract_name"),
            contract_value=extracted_data.get("contract_value"),
            contractor_name=extracted_data.get("contractor_name"),
            subcontractor_name=extracted_data.get("subcontractor_name"),
            owner_name=extracted_data.get("owner_name"),
            agreement_date=extracted_data.get("agreement_date"),
            start_date=extracted_data.get("start_date"),
            end_date=extracted_data.get("end_date"),
            project_location=extracted_data.get("project_location"),
            work_description=extracted_data.get("work_description"),
            project_type=extracted_data.get("project_type"),
            payment_terms=extracted_data.get("payment_terms"),
            retainage_percentage=extracted_data.get("retainage_percentage"),
            insurance_required=extracted_data.get("insurance_required", False),
            bond_required=extracted_data.get("bond_required", False),
            insurance_amount=extracted_data.get("insurance_amount"),
            bond_amount=extracted_data.get("bond_amount"),
            ai_provider=extracted_data.get("ai_provider"),
            confidence_score=extracted_data.get("confidence_score"),
        )

        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)

        return {
            "message": "Contract analyzed successfully using Claude AI",
            "contract_id": contract.id,
            "analysis_id": db_analysis.id,
            "extracted_data": {
                "contract_number": db_analysis.contract_number,
                "contract_name": db_analysis.contract_name,
                "contract_value": (
                    str(db_analysis.contract_value)
                    if db_analysis.contract_value
                    else None
                ),
                "contractor_name": db_analysis.contractor_name,
                "subcontractor_name": db_analysis.subcontractor_name,
                "owner_name": db_analysis.owner_name,
                "project_location": db_analysis.project_location,
                "work_description": db_analysis.work_description,
                "project_type": db_analysis.project_type,
                "agreement_date": (
                    db_analysis.agreement_date.isoformat()
                    if db_analysis.agreement_date
                    else None
                ),
                "start_date": (
                    db_analysis.start_date.isoformat()
                    if db_analysis.start_date
                    else None
                ),
                "end_date": (
                    db_analysis.end_date.isoformat() if db_analysis.end_date else None
                ),
                "insurance_required": db_analysis.insurance_required,
                "bond_required": db_analysis.bond_required,
            },
            "analysis_provider": db_analysis.ai_provider,
            "fields_extracted": analysis_result.get("fields_extracted", 0),
            "total_possible_fields": analysis_result.get("total_possible_fields", 18),
            "text_length": analysis_result.get("text_length"),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Contract analysis failed: {str(e)}"
        )


@router.get("/list", response_model=ContractListResponse)
async def list_contractss(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all contracts with their analysis status
    """

    # Join contracts with their analyses
    contracts_with_analysis = (
        db.query(Contract, ContractAnalysis)
        .outerjoin(ContractAnalysis, Contract.id == ContractAnalysis.contract_id)
        .order_by(Contract.created_at.desc())
        .all()
    )

    contract_list = []
    for contract, analysis in contracts_with_analysis:
        is_analyzed = analysis is not None

        contract_info = {
            "id": contract.id,
            "filename": contract.filename,
            "created_at": contract.created_at.isoformat(),
            "is_processed": contract.is_processed,
            "is_analyzed": is_analyzed,
            "text_length": len(contract.raw_text) if contract.raw_text else 0,
        }

        # Add analysis data if available
        if analysis:
            contract_info.update(
                {
                    "analysis_id": analysis.id,
                    "contract_number": analysis.contract_number,
                    "contract_name": analysis.contract_name,
                    "contract_value": (
                        str(analysis.contract_value)
                        if analysis.contract_value
                        else None
                    ),
                    "contractor_name": analysis.contractor_name,
                    "subcontractor_name": analysis.subcontractor_name,
                    "analysis_date": analysis.analysis_date.isoformat(),
                    "ai_provider": analysis.ai_provider,
                }
            )
        else:
            contract_info.update(
                {
                    "analysis_id": None,
                    "contract_number": None,
                    "contract_name": None,
                    "contract_value": None,
                    "contractor_name": None,
                    "subcontractor_name": None,
                    "analysis_date": None,
                    "ai_provider": None,
                }
            )

        contract_list.append(contract_info)

    return {"contracts": contract_list, "total_count": len(contract_list)}


@router.get("/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed contract information including analysis data
    """

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Get analysis data if it exists
    analysis = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract_id)
        .first()
    )

    response = {
        "id": contract.id,
        "filename": contract.filename,
        "created_at": contract.created_at.isoformat(),
        "is_processed": contract.is_processed,
        "text_length": len(contract.raw_text) if contract.raw_text else 0,
        "raw_text_preview": (
            contract.raw_text[:500] + "..."
            if contract.raw_text and len(contract.raw_text) > 500
            else contract.raw_text
        ),
    }

    # Add comprehensive analysis data if available
    if analysis:
        response.update(
            {
                "analysis": {
                    "id": analysis.id,
                    "contract_number": analysis.contract_number,
                    "contract_name": analysis.contract_name,
                    "contract_value": (
                        str(analysis.contract_value)
                        if analysis.contract_value
                        else None
                    ),
                    "contractor_name": analysis.contractor_name,
                    "subcontractor_name": analysis.subcontractor_name,
                    "owner_name": analysis.owner_name,
                    "project_location": analysis.project_location,
                    "work_description": analysis.work_description,
                    "project_type": analysis.project_type,
                    "payment_terms": analysis.payment_terms,
                    "retainage_percentage": (
                        str(analysis.retainage_percentage)
                        if analysis.retainage_percentage
                        else None
                    ),
                    "agreement_date": (
                        analysis.agreement_date.isoformat()
                        if analysis.agreement_date
                        else None
                    ),
                    "start_date": (
                        analysis.start_date.isoformat() if analysis.start_date else None
                    ),
                    "end_date": (
                        analysis.end_date.isoformat() if analysis.end_date else None
                    ),
                    "insurance_required": analysis.insurance_required,
                    "bond_required": analysis.bond_required,
                    "insurance_amount": (
                        str(analysis.insurance_amount)
                        if analysis.insurance_amount
                        else None
                    ),
                    "bond_amount": (
                        str(analysis.bond_amount) if analysis.bond_amount else None
                    ),
                    "ai_provider": analysis.ai_provider,
                    "analysis_date": analysis.analysis_date.isoformat(),
                    "confidence_score": (
                        str(analysis.confidence_score)
                        if analysis.confidence_score
                        else None
                    ),
                }
            }
        )
    else:
        response["analysis"] = None

    return response


@router.get("/{contract_id}/analysis")
async def get_contract_analysis_only(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get only the analysis data for a contract
    """

    analysis = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract_id)
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=404, detail="No analysis found for this contract"
        )

    return {
        "analysis_id": analysis.id,
        "contract_id": analysis.contract_id,
        "contract_number": analysis.contract_number,
        "contract_name": analysis.contract_name,
        "contract_value": (
            str(analysis.contract_value) if analysis.contract_value else None
        ),
        "contractor_name": analysis.contractor_name,
        "subcontractor_name": analysis.subcontractor_name,
        "owner_name": analysis.owner_name,
        "project_location": analysis.project_location,
        "work_description": analysis.work_description,
        "project_type": analysis.project_type,
        "payment_terms": analysis.payment_terms,
        "retainage_percentage": (
            str(analysis.retainage_percentage)
            if analysis.retainage_percentage
            else None
        ),
        "agreement_date": (
            analysis.agreement_date.isoformat() if analysis.agreement_date else None
        ),
        "start_date": analysis.start_date.isoformat() if analysis.start_date else None,
        "end_date": analysis.end_date.isoformat() if analysis.end_date else None,
        "insurance_required": analysis.insurance_required,
        "bond_required": analysis.bond_required,
        "insurance_amount": (
            str(analysis.insurance_amount) if analysis.insurance_amount else None
        ),
        "bond_amount": str(analysis.bond_amount) if analysis.bond_amount else None,
        "ai_provider": analysis.ai_provider,
        "analysis_date": analysis.analysis_date.isoformat(),
        "confidence_score": (
            str(analysis.confidence_score) if analysis.confidence_score else None
        ),
    }
