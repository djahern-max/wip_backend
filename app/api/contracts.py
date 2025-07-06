import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.contract import Contract
from app.schemas.contract import Contract as ContractSchema
from app.api.auth import get_current_active_user
from app.models.user import User

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
            "contract_data": {
                "contract_number": contract.contract_number,
                "contract_name": contract.contract_name,
                "contract_value": (
                    str(contract.contract_value) if contract.contract_value else None
                ),
            },
        }

    try:
        # Use AI to analyze the extracted text
        from app.services.contract_parser import parse_contract_data

        extracted_data = parse_contract_data(contract.raw_text)

        # Update contract with extracted data
        contract.contract_number = extracted_data.get("contract_number")
        contract.contract_name = extracted_data.get("contract_name")
        contract.contract_value = extracted_data.get("contract_value")

        db.commit()

        return {
            "message": "Contract analyzed successfully using AI",
            "contract_id": contract.id,
            "extracted_data": {
                "contract_number": contract.contract_number,
                "contract_name": contract.contract_name,
                "contract_value": (
                    str(contract.contract_value) if contract.contract_value else None
                ),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Contract analysis failed: {str(e)}"
        )
