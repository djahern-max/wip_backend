# app/api/contracts.py - Refactored for encryption-only models

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis
from app.api.auth import get_current_active_user
from app.models.user import User
from app.services.simplified_contract_analyzer import SimplifiedContractAnalyzer
from app.core.config import settings

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


# Add this to app/api/contracts.py - replace the existing analyze endpoint


@router.post("/analyze/{contract_id}")
async def analyze_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Simplified contract analysis - extract key information only"""

    print(f"🔍 Starting simplified analysis for contract_id: {contract_id}")

    # Check if contract exists
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        print(f"❌ Contract {contract_id} not found")
        raise HTTPException(status_code=404, detail="Contract not found")

    print(f"✅ Contract found: {contract.filename}")

    # Check if already analyzed
    existing_analysis = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract_id)
        .first()
    )

    if existing_analysis:
        print(f"ℹ️ Contract already analyzed (analysis_id: {existing_analysis.id})")

        # Return existing analysis in clean JSON format
        return {
            "success": True,
            "message": "Contract already analyzed",
            "contract_info": {
                "contract_id": contract.id,
                "filename": contract.filename,
                "analysis_id": existing_analysis.id,
                "analysis_date": existing_analysis.analysis_date.isoformat(),
            },
            "key_findings": {
                "contract_number": existing_analysis.contract_number,
                "contract_name": existing_analysis.contract_name,
                "contract_value": (
                    float(existing_analysis.contract_value)
                    if existing_analysis.contract_value
                    else None
                ),
                "contractor_name": existing_analysis.contractor_name,
                "owner_name": existing_analysis.owner_name,
                "project_location": existing_analysis.project_location,
                "project_type": existing_analysis.project_type,
                "agreement_date": (
                    existing_analysis.agreement_date.isoformat()
                    if existing_analysis.agreement_date
                    else None
                ),
                "work_description": existing_analysis.work_description,
            },
            "metadata": {
                "ai_provider": existing_analysis.ai_provider,
                "confidence_score": (
                    float(existing_analysis.confidence_score)
                    if existing_analysis.confidence_score
                    else None
                ),
                "status": "previously_analyzed",
            },
        }

    # Get decrypted text for analysis
    try:
        raw_text = contract.raw_text
        print(f"📄 Raw text length: {len(raw_text) if raw_text else 0}")
    except Exception as e:
        print(f"❌ Decryption failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to decrypt contract text: {str(e)}"
        )

    if not raw_text:
        print("❌ No text found after decryption")
        raise HTTPException(
            status_code=422, detail="No text found - extract text first"
        )

    if len(raw_text.strip()) < 100:
        print(f"❌ Text too short: {len(raw_text.strip())} characters")
        raise HTTPException(
            status_code=422, detail="Contract text too short for analysis"
        )

    # Check API key
    if not settings.anthropic_api_key:
        print("❌ No Anthropic API key configured")
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    try:
        print("🤖 Initializing simplified Claude analyzer...")
        from app.services.simplified_contract_analyzer import SimplifiedContractAnalyzer

        analyzer = SimplifiedContractAnalyzer()

        print("📊 Starting key contract analysis...")
        analysis_result = analyzer.analyze_contract(raw_text)

        if not analysis_result["success"]:
            print("❌ Analysis result indicates failure")
            raise HTTPException(status_code=500, detail="Contract analysis failed")

        print("✅ Analysis successful, extracting key data...")
        extracted_data = analysis_result["data"]

        # Create simplified analysis record
        print("💾 Creating database record...")
        db_analysis = ContractAnalysis(
            contract_id=contract_id,
            # Key fields
            contract_number=extracted_data.get("contract_number"),
            contract_value=extracted_data.get("contract_value"),
            agreement_date=extracted_data.get("agreement_date"),
            project_type=extracted_data.get("project_type"),
            ai_provider=extracted_data.get("ai_provider"),
            confidence_score=extracted_data.get("confidence_score"),
        )

        # Set encrypted fields using properties
        db_analysis.contractor_name = extracted_data.get("contractor_name")
        db_analysis.owner_name = extracted_data.get("owner_name")
        db_analysis.contract_name = extracted_data.get("contract_name")
        db_analysis.project_location = extracted_data.get("project_location")
        db_analysis.work_description = extracted_data.get("work_description")

        print("💾 Saving to database...")
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)

        print(f"✅ Analysis complete! Analysis ID: {db_analysis.id}")

        # Return clean JSON response for frontend
        return {
            "success": True,
            "message": "Contract analyzed successfully",
            "contract_info": {
                "contract_id": contract.id,
                "filename": contract.filename,
                "analysis_id": db_analysis.id,
                "analysis_date": db_analysis.analysis_date.isoformat(),
            },
            "key_findings": {
                "contract_number": db_analysis.contract_number,
                "contract_name": db_analysis.contract_name,
                "contract_value": (
                    float(db_analysis.contract_value)
                    if db_analysis.contract_value
                    else None
                ),
                "contractor_name": db_analysis.contractor_name,
                "owner_name": db_analysis.owner_name,
                "project_location": db_analysis.project_location,
                "project_type": db_analysis.project_type,
                "agreement_date": (
                    db_analysis.agreement_date.isoformat()
                    if db_analysis.agreement_date
                    else None
                ),
                "work_description": db_analysis.work_description,
            },
            "analysis_summary": analysis_result.get("summary", ""),
            "metadata": {
                "ai_provider": db_analysis.ai_provider,
                "confidence_score": (
                    float(db_analysis.confidence_score)
                    if db_analysis.confidence_score
                    else None
                ),
                "fields_extracted": analysis_result.get("fields_extracted", 0),
                "total_possible_fields": analysis_result.get(
                    "total_possible_fields", 9
                ),
                "text_length": len(raw_text),
                "status": "newly_analyzed",
            },
        }

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        error_msg = str(e)

        if "overloaded" in error_msg.lower() or "529" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Claude AI service is temporarily overloaded. Please try again in a few minutes.",
            )
        elif "rate limited" in error_msg.lower() or "429" in error_msg:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait a moment before trying again.",
            )
        else:
            raise HTTPException(
                status_code=500, detail=f"Contract analysis failed: {str(e)}"
            )


# Add a summary endpoint for quick contract overview
@router.get("/summary/{contract_id}")
async def get_contract_summary(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get contract summary - either from analysis or basic file info"""

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Check if analysis exists
    analysis = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract_id)
        .first()
    )

    if analysis:
        # Return analyzed data
        return {
            "contract_id": contract.id,
            "filename": contract.filename,
            "status": "analyzed",
            "analysis_date": analysis.analysis_date.isoformat(),
            "key_info": {
                "contract_name": analysis.contract_name,
                "contractor_name": analysis.contractor_name,
                "contract_value": (
                    float(analysis.contract_value) if analysis.contract_value else None
                ),
                "project_type": analysis.project_type,
                "project_location": analysis.project_location,
            },
            "actions": ["view_full_analysis", "export_data"],
        }
    else:
        # Return basic info with analysis option
        try:
            text_length = len(contract.raw_text) if contract.raw_text else 0
        except:
            text_length = 0

        return {
            "contract_id": contract.id,
            "filename": contract.filename,
            "status": "not_analyzed",
            "uploaded_date": contract.created_at.isoformat(),
            "text_length": text_length,
            "actions": ["analyze_contract"] if text_length > 0 else ["extract_text"],
        }
