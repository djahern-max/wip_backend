from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.contract import Contract
from app.api.auth import get_current_active_user
from app.models.user import User
from app.services.claude_contract_analyzer import ClaudeContractAnalyzer

router = APIRouter()


@router.post("/extract-text")
async def extract_contract_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
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

        # Save to database using existing table structure
        db_contract = Contract(
            filename=file.filename,
            raw_text=raw_text,
            is_processed=True,
            contract_number=None,
            contract_name=None,
            contract_value=None,
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


@router.post("/analyze/{contract_id}")
async def analyze_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Analyze contract using Claude AI to extract key information
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
    if contract.contract_number and contract.contract_name and contract.contract_value:
        return {
            "message": "Contract already analyzed",
            "contract_id": contract.id,
            "extracted_data": {
                "contract_number": contract.contract_number,
                "contract_name": contract.contract_name,
                "contract_value": (
                    str(contract.contract_value) if contract.contract_value else None
                ),
            },
            "analysis_provider": "previously_analyzed",
        }

    try:
        # Initialize Claude analyzer
        analyzer = ClaudeContractAnalyzer()

        # Analyze the contract
        analysis_result = analyzer.analyze_contract(contract.raw_text)

        if not analysis_result["success"]:
            raise HTTPException(status_code=500, detail="Contract analysis failed")

        # Update contract with extracted data
        contract.contract_number = analysis_result.get("contract_number")
        contract.contract_name = analysis_result.get("contract_name")
        contract.contract_value = analysis_result.get("contract_value")

        db.commit()
        db.refresh(contract)

        return {
            "message": "Contract analyzed successfully using Claude AI",
            "contract_id": contract.id,
            "extracted_data": {
                "contract_number": contract.contract_number,
                "contract_name": contract.contract_name,
                "contract_value": (
                    str(contract.contract_value) if contract.contract_value else None
                ),
            },
            "analysis_provider": analysis_result.get("analysis_provider"),
            "text_length": analysis_result.get("text_length"),
            "processing_time": "fast",
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
    """
    List all contracts with their analysis status
    """

    contracts = db.query(Contract).order_by(Contract.created_at.desc()).all()

    contract_list = []
    for contract in contracts:
        is_analyzed = bool(
            contract.contract_number
            or contract.contract_name
            or contract.contract_value
        )

        contract_list.append(
            {
                "id": contract.id,
                "filename": contract.filename,
                "created_at": contract.created_at,
                "is_processed": contract.is_processed,
                "is_analyzed": is_analyzed,
                "text_length": len(contract.raw_text) if contract.raw_text else 0,
                "contract_number": contract.contract_number,
                "contract_name": contract.contract_name,
                "contract_value": (
                    str(contract.contract_value) if contract.contract_value else None
                ),
            }
        )

    return {"contracts": contract_list, "total_count": len(contract_list)}


@router.get("/{contract_id}")
async def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed contract information
    """

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {
        "id": contract.id,
        "filename": contract.filename,
        "created_at": contract.created_at,
        "is_processed": contract.is_processed,
        "text_length": len(contract.raw_text) if contract.raw_text else 0,
        "contract_number": contract.contract_number,
        "contract_name": contract.contract_name,
        "contract_value": (
            str(contract.contract_value) if contract.contract_value else None
        ),
        "raw_text_preview": (
            contract.raw_text[:500] + "..."
            if contract.raw_text and len(contract.raw_text) > 500
            else contract.raw_text
        ),
    }
