import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.contract import Contract
from app.schemas.contract import Contract as ContractSchema
from app.api.auth import get_current_active_user
from app.models.user import User

router = APIRouter()

UPLOAD_DIR = "uploads/contracts"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Read and save file to disk
    file_content = await file.read()
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # Save to database (no processing yet)
    db_contract = Contract(
        filename=file.filename,
        contract_number=None,
        contract_name=None,
        contract_value=None,
        raw_text=None,
        is_processed=False
    )
    
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    
    return {
        "message": "Contract uploaded successfully",
        "contract_id": db_contract.id,
        "filename": file.filename,
        "status": "uploaded, ready for analysis"
    }


@router.post("/analyze/{contract_id}")
async def analyze_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get contract from database
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if contract.is_processed:
        return {
            "message": "Contract already analyzed",
            "contract_data": {
                "contract_number": contract.contract_number,
                "contract_name": contract.contract_name,
                "contract_value": str(contract.contract_value) if contract.contract_value else None
            }
        }
    
    # Analyze the file using AI - NO FALLBACKS
    file_path = os.path.join(UPLOAD_DIR, contract.filename)
    
    try:
        # Step 1: Extract text from PDF
        from app.services.pdf_extractor import extract_text_from_pdf
        raw_text = extract_text_from_pdf(file_path)
        
        if not raw_text:
            raise HTTPException(
                status_code=422, 
                detail="Failed to extract text from PDF. Document may be image-based or corrupted."
            )
        
        # Step 2: Use AI to analyze the extracted text
        from app.services.contract_parser import parse_contract_data
        extracted_data = parse_contract_data(raw_text)
        
        # Step 3: Validate that we got meaningful data
        if not any([
            extracted_data.get("contract_number"),
            extracted_data.get("contract_name"),
            extracted_data.get("contract_value")
        ]):
            raise HTTPException(
                status_code=422,
                detail="AI analysis failed to extract any meaningful contract data"
            )
        
        # Step 4: Update contract with extracted data
        contract.raw_text = raw_text
        contract.contract_number = extracted_data.get("contract_number")
        contract.contract_name = extracted_data.get("contract_name")
        contract.contract_value = extracted_data.get("contract_value")
        contract.is_processed = True
        
        db.commit()
        
        return {
            "message": "Contract analyzed successfully using AI",
            "contract_id": contract.id,
            "extracted_data": {
                "contract_number": contract.contract_number,
                "contract_name": contract.contract_name,
                "contract_value": str(contract.contract_value) if contract.contract_value else None
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Convert any other exception to a clear HTTP error
        raise HTTPException(
            status_code=500,
            detail=f"Contract analysis failed: {str(e)}"
        )


@router.get("/", response_model=list[ContractSchema])
async def list_contracts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    contracts = db.query(Contract).all()
    return contracts


@router.get("/{contract_id}", response_model=ContractSchema)
async def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract
