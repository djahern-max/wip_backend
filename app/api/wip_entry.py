# app/api/wip_entry.py - Filename-based ultra simple API
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from decimal import Decimal
from app.models.wip_entry import WIPEntry
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis
from app.models.user import User
from app.core.database import get_db
from app.api.auth import get_current_active_user
from app.schemas.wip_entry import WIPCreateRequest, WIPUpdateRequest


router = APIRouter()


@router.get("/available-contracts")
async def get_available_contracts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get list of contracts available for WIP entry creation
    Shows user-friendly filenames instead of contract IDs
    """

    # Get contracts that have been analyzed but don't have WIP entries yet
    available_contracts = (
        db.query(Contract, ContractAnalysis)
        .join(ContractAnalysis, Contract.id == ContractAnalysis.contract_id)
        .outerjoin(WIPEntry, Contract.id == WIPEntry.contract_id)
        .filter(WIPEntry.id.is_(None))  # No existing WIP entry
        .all()
    )

    contracts_list = []
    for contract, analysis in available_contracts:
        contracts_list.append(
            {
                "filename": contract.filename,  # This is what user will use
                "contract_name": analysis.contract_name or "Unnamed Contract",
                "contractor_name": analysis.contractor_name,
                "contract_value": (
                    float(analysis.contract_value) if analysis.contract_value else None
                ),
                "project_location": analysis.project_location,
                "uploaded_date": contract.created_at.isoformat(),
            }
        )

    return {
        "available_contracts": contracts_list,
        "total_count": len(contracts_list),
        "message": f"Found {len(contracts_list)} contracts ready for WIP entry creation",
        "usage": "Use the 'filename' field when creating WIP entries",
    }


@router.get("/wip-preview")
async def preview_wip_data(
    filename: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Preview WIP data using filename
    Example: GET /wip/wip-preview?filename=Bridge_Contract.pdf
    """

    contract = db.query(Contract).filter(Contract.filename == filename).first()
    if not contract:
        raise HTTPException(
            status_code=404, detail=f"Contract with filename '{filename}' not found"
        )

    # Check if WIP entry already exists
    existing_wip = (
        db.query(WIPEntry).filter(WIPEntry.contract_id == contract.id).first()
    )
    if existing_wip:
        return {
            "filename": filename,
            "status": "wip_exists",
            "existing_wip": {
                "wip_id": existing_wip.id,
                "job_number": existing_wip.job_number,
                "job_name": existing_wip.job_name,
                "contract_amount": float(existing_wip.contract_amount),
            },
            "message": "WIP entry already exists for this contract",
        }

    analysis = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract.id)
        .first()
    )

    if not analysis:
        return {
            "filename": filename,
            "status": "not_analyzed",
            "message": f"Contract '{filename}' not analyzed yet. Analyze it first.",
            "auto_populate_available": False,
        }

    # Show what would be auto-populated
    job_name = analysis.contract_name or filename.replace(".pdf", "")
    contract_amount = analysis.contract_value or Decimal("0.00")

    return {
        "filename": filename,
        "status": "ready_for_wip",
        "contract_info": {
            "contractor_name": analysis.contractor_name,
            "project_location": analysis.project_location,
            "uploaded_date": contract.created_at.isoformat(),
        },
        "auto_populate_preview": {
            "job_name": job_name,
            "contract_amount": float(contract_amount),
        },
        "user_needs_to_provide": ["job_number"],
        "message": "Ready to create WIP entry - just provide job_number",
    }


@router.post("/wip-entry")
async def create_wip_entry(
    request: WIPCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create WIP entry using filename - ULTRA SIMPLE!

    Example request:
    {
        "filename": "Bridge_Contract.pdf",
        "job_number": "CT-2024-001"
    }
    """

    # Find contract by filename
    contract = db.query(Contract).filter(Contract.filename == request.filename).first()
    if not contract:
        raise HTTPException(
            status_code=404,
            detail=f"Contract with filename '{request.filename}' not found",
        )

    # Check if WIP entry already exists
    existing_entry = (
        db.query(WIPEntry).filter(WIPEntry.contract_id == contract.id).first()
    )
    if existing_entry:
        raise HTTPException(
            status_code=400, detail=f"WIP entry already exists for '{request.filename}'"
        )

    # Get analysis data
    analysis = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract.id)
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=400,
            detail=f"Contract '{request.filename}' must be analyzed first",
        )

    # Auto-populate from analysis
    job_name = analysis.contract_name or request.filename.replace(".pdf", "")
    contract_amount = analysis.contract_value or Decimal("0.00")

    # Create WIP entry
    wip_entry = WIPEntry(
        contract_id=contract.id,
        job_number=request.job_number,
        job_name=job_name,
        contract_amount=contract_amount,
    )

    db.add(wip_entry)
    db.commit()
    db.refresh(wip_entry)

    return {
        "message": f"WIP entry created successfully for '{request.filename}'",
        "wip_entry": {
            "id": wip_entry.id,
            "filename": request.filename,
            "job_number": wip_entry.job_number,
            "job_name": wip_entry.job_name,
            "contract_amount": float(wip_entry.contract_amount),
        },
        "auto_populated": {
            "job_name": f"From contract analysis: '{analysis.contract_name}'",
            "contract_amount": f"From contract analysis: ${wip_entry.contract_amount:,.2f}",
        },
    }


@router.put("/wip-entry/{wip_id}")
async def update_wip_entry(
    wip_id: int,
    update_data: WIPUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update WIP entry"""
    wip_entry = db.query(WIPEntry).filter(WIPEntry.id == wip_id).first()
    if not wip_entry:
        raise HTTPException(status_code=404, detail="WIP entry not found")

    if update_data.job_number is not None:
        wip_entry.job_number = update_data.job_number
    if update_data.job_name is not None:
        wip_entry.job_name = update_data.job_name
    if update_data.contract_amount is not None:
        wip_entry.contract_amount = update_data.contract_amount

    db.commit()
    db.refresh(wip_entry)

    return {
        "message": "WIP entry updated successfully",
        "wip_entry": {
            "id": wip_entry.id,
            "job_number": wip_entry.job_number,
            "job_name": wip_entry.job_name,
            "contract_amount": float(wip_entry.contract_amount),
        },
    }


@router.get("/wip-entry/{wip_id}")
async def get_wip_entry(
    wip_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get specific WIP entry"""
    wip_entry = db.query(WIPEntry).filter(WIPEntry.id == wip_id).first()
    if not wip_entry:
        raise HTTPException(status_code=404, detail="WIP entry not found")

    return {
        "id": wip_entry.id,
        "contract_id": wip_entry.contract_id,
        "job_number": wip_entry.job_number,
        "job_name": wip_entry.job_name,
        "contract_amount": float(wip_entry.contract_amount),
    }


@router.get("/wip-entries")
async def list_wip_entries(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all WIP entries with contract filenames"""

    wip_entries_with_contracts = (
        db.query(WIPEntry, Contract)
        .join(Contract, WIPEntry.contract_id == Contract.id)
        .all()
    )

    return {
        "wip_entries": [
            {
                "id": wip_entry.id,
                "filename": contract.filename,  # Show filename instead of contract_id
                "job_number": wip_entry.job_number,
                "job_name": wip_entry.job_name,
                "contract_amount": float(wip_entry.contract_amount),
            }
            for wip_entry, contract in wip_entries_with_contracts
        ],
        "total_count": len(wip_entries_with_contracts),
    }


# Add this endpoint to your wip_entry.py for debugging


@router.get("/contracts-status")
async def get_contracts_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Debug endpoint - shows status of all contracts and why they may not be available for WIP
    """

    # Get all contracts with their analysis and WIP status
    contracts_info = (
        db.query(Contract)
        .outerjoin(ContractAnalysis, Contract.id == ContractAnalysis.contract_id)
        .outerjoin(WIPEntry, Contract.id == WIPEntry.contract_id)
        .all()
    )

    contracts_list = []
    available_count = 0

    for contract in contracts_info:
        # Get related analysis and WIP data
        analysis = (
            db.query(ContractAnalysis)
            .filter(ContractAnalysis.contract_id == contract.id)
            .first()
        )
        wip_entry = (
            db.query(WIPEntry).filter(WIPEntry.contract_id == contract.id).first()
        )

        # Determine status and availability
        has_analysis = analysis is not None
        has_wip = wip_entry is not None

        if has_analysis and not has_wip:
            status = "AVAILABLE_FOR_WIP"
            available_count += 1
        elif not has_analysis:
            status = "NEEDS_ANALYSIS"
        elif has_wip:
            status = "HAS_WIP_ALREADY"
        else:
            status = "UNKNOWN"

        contract_info = {
            "contract_id": contract.id,
            "filename": contract.filename,
            "status": status,
            "uploaded_date": contract.created_at.isoformat(),
            "has_analysis": has_analysis,
            "has_wip_entry": has_wip,
        }

        # Add analysis info if available
        if analysis:
            contract_info["analysis_info"] = {
                "contract_name": analysis.contract_name,
                "contractor_name": analysis.contractor_name,
                "contract_value": (
                    float(analysis.contract_value) if analysis.contract_value else None
                ),
                "analyzed_date": analysis.analysis_date.isoformat(),
            }

        # Add WIP info if exists
        if wip_entry:
            contract_info["wip_info"] = {
                "wip_id": wip_entry.id,
                "job_number": wip_entry.job_number,
                "job_name": wip_entry.job_name,
            }

        contracts_list.append(contract_info)

    # Summary counts
    total_contracts = len(contracts_list)
    analyzed_contracts = len([c for c in contracts_list if c["has_analysis"]])
    contracts_with_wip = len([c for c in contracts_list if c["has_wip_entry"]])
    needs_analysis = len([c for c in contracts_list if not c["has_analysis"]])

    return {
        "summary": {
            "total_contracts": total_contracts,
            "analyzed_contracts": analyzed_contracts,
            "contracts_with_wip": contracts_with_wip,
            "available_for_wip": available_count,
            "needs_analysis": needs_analysis,
        },
        "contracts": contracts_list,
        "next_steps": {
            "if_no_contracts": "Upload PDFs using POST /contracts/extract-text",
            "if_needs_analysis": "Analyze contracts using POST /contracts/analyze/{contract_id}",
            "if_available": "Create WIP entries using POST /wip/wip-entry with filename",
        },
    }
