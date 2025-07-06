# app/api/contracts.py - Refactored for encryption-only models

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis
from app.api.auth import get_current_active_user
from app.models.user import User
from app.services.claude_contract_analyzer import ComprehensiveClaudeAnalyzer

router = APIRouter()


@router.post("/extract-text")
async def extract_contract_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Extract text from PDF and store encrypted in contracts table"""

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    try:
        file_content = await file.read()

        from app.services.pdf_extractor import extract_text_from_uploaded_file

        raw_text = extract_text_from_uploaded_file(file_content)

        if not raw_text:
            raise HTTPException(
                status_code=422, detail="Failed to extract text from PDF."
            )

        # Create contract with ENCRYPTED storage only
        db_contract = Contract(
            filename=file.filename,
            is_processed=True,
        )

        # This will automatically encrypt the text
        db_contract.raw_text = raw_text

        db.add(db_contract)
        db.commit()
        db.refresh(db_contract)

        return {
            "message": "Text extracted and encrypted successfully",
            "contract_id": db_contract.id,
            "text_length": len(raw_text),
            "preview": raw_text[:200] + "..." if len(raw_text) > 200 else raw_text,
            "security_status": "ENCRYPTED",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")


@router.post("/analyze/{contract_id}")
async def analyze_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Analyze contract using Claude AI - FULLY ENCRYPTED PIPELINE"""

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Get decrypted text for analysis
    raw_text = contract.raw_text
    if not raw_text:
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
                "contract_name": existing_analysis.contract_name,  # Auto-decrypted
                "contract_value": (
                    str(existing_analysis.contract_value)
                    if existing_analysis.contract_value
                    else None
                ),
                "contractor_name": existing_analysis.contractor_name,  # Auto-decrypted
                "subcontractor_name": existing_analysis.subcontractor_name,  # Auto-decrypted
                "owner_name": existing_analysis.owner_name,  # Auto-decrypted
                "project_location": existing_analysis.project_location,  # Auto-decrypted
                "work_description": existing_analysis.work_description,  # Auto-decrypted
                "payment_terms": existing_analysis.payment_terms,  # Auto-decrypted
                "agreement_date": (
                    existing_analysis.agreement_date.isoformat()
                    if existing_analysis.agreement_date
                    else None
                ),
            },
            "analysis_provider": existing_analysis.ai_provider,
            "security_status": "ENCRYPTED",
        }

    try:
        analyzer = ComprehensiveClaudeAnalyzer()
        analysis_result = analyzer.analyze_contract(raw_text)

        if not analysis_result["success"]:
            raise HTTPException(status_code=500, detail="Contract analysis failed")

        extracted_data = analysis_result["data"]

        # Create analysis with ENCRYPTED sensitive data
        db_analysis = ContractAnalysis(
            contract_id=contract_id,
            # Non-sensitive fields (plain text)
            contract_number=extracted_data.get("contract_number"),
            contract_value=extracted_data.get("contract_value"),
            agreement_date=extracted_data.get("agreement_date"),
            start_date=extracted_data.get("start_date"),
            end_date=extracted_data.get("end_date"),
            project_type=extracted_data.get("project_type"),
            retainage_percentage=extracted_data.get("retainage_percentage"),
            insurance_required=extracted_data.get("insurance_required", False),
            bond_required=extracted_data.get("bond_required", False),
            ai_provider=extracted_data.get("ai_provider"),
            confidence_score=extracted_data.get("confidence_score"),
        )

        # Sensitive fields (automatically encrypted via properties)
        db_analysis.contractor_name = extracted_data.get("contractor_name")
        db_analysis.subcontractor_name = extracted_data.get("subcontractor_name")
        db_analysis.owner_name = extracted_data.get("owner_name")
        db_analysis.contract_name = extracted_data.get("contract_name")
        db_analysis.project_location = extracted_data.get("project_location")
        db_analysis.work_description = extracted_data.get("work_description")
        db_analysis.payment_terms = extracted_data.get("payment_terms")
        db_analysis.insurance_amount = extracted_data.get("insurance_amount")
        db_analysis.bond_amount = extracted_data.get("bond_amount")

        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)

        return {
            "message": "Contract analyzed successfully - FULLY ENCRYPTED",
            "contract_id": contract.id,
            "analysis_id": db_analysis.id,
            "extracted_data": {
                "contract_number": db_analysis.contract_number,
                "contract_name": db_analysis.contract_name,  # Auto-decrypted
                "contract_value": (
                    str(db_analysis.contract_value)
                    if db_analysis.contract_value
                    else None
                ),
                "contractor_name": db_analysis.contractor_name,  # Auto-decrypted
                "subcontractor_name": db_analysis.subcontractor_name,  # Auto-decrypted
                "owner_name": db_analysis.owner_name,  # Auto-decrypted
                "project_location": db_analysis.project_location,  # Auto-decrypted
                "work_description": db_analysis.work_description,  # Auto-decrypted
                "project_type": db_analysis.project_type,
                "payment_terms": db_analysis.payment_terms,  # Auto-decrypted
                "agreement_date": (
                    db_analysis.agreement_date.isoformat()
                    if db_analysis.agreement_date
                    else None
                ),
                "insurance_required": db_analysis.insurance_required,
                "bond_required": db_analysis.bond_required,
                "insurance_amount": (
                    str(db_analysis.insurance_amount)
                    if db_analysis.insurance_amount
                    else None
                ),
                "bond_amount": (
                    str(db_analysis.bond_amount) if db_analysis.bond_amount else None
                ),
            },
            "analysis_provider": db_analysis.ai_provider,
            "fields_extracted": analysis_result.get("fields_extracted", 0),
            "total_possible_fields": analysis_result.get("total_possible_fields", 18),
            "security_status": "FULLY_ENCRYPTED",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Contract analysis failed: {str(e)}"
        )


@router.get("/list")
async def list_contracts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all contracts with analysis status - encryption transparent"""

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
            "text_length": (
                len(contract.raw_text) if contract.raw_text else 0
            ),  # Auto-decrypted
            "security_status": "ENCRYPTED",
        }

        if analysis:
            contract_info.update(
                {
                    "analysis_id": analysis.id,
                    "contract_number": analysis.contract_number,
                    "contract_name": analysis.contract_name,  # Auto-decrypted
                    "contract_value": (
                        str(analysis.contract_value)
                        if analysis.contract_value
                        else None
                    ),
                    "contractor_name": analysis.contractor_name,  # Auto-decrypted
                    "subcontractor_name": analysis.subcontractor_name,  # Auto-decrypted
                    "analysis_date": analysis.analysis_date.isoformat(),
                    "ai_provider": analysis.ai_provider,
                }
            )

        contract_list.append(contract_info)

    return {
        "contracts": contract_list,
        "total_count": len(contract_list),
        "security_status": "ALL_DATA_ENCRYPTED",
    }
