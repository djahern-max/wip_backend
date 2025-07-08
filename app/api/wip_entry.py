from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from decimal import Decimal
import json
from app.models import WIPEntry, User
from app.core.database import get_db

router = APIRouter()


@router.post("/wip-entry")
async def create_wip_entry(
    contract_id: int,
    job_number: str,
    business_field: str,
    job_name: str,
    contract_amount: Decimal,
    db: Session = Depends(get_db),
):
    """
    Create a new WIP entry with automatic deviation detection
    """

    # Check if WIP entry already exists for this contract
    existing_entry = (
        db.query(WIPEntry).filter(WIPEntry.contract_id == contract_id).first()
    )
    if existing_entry:
        raise HTTPException(
            status_code=400, detail="WIP entry already exists for this contract"
        )

    # Create new WIP entry
    wip_entry = WIPEntry(
        contract_id=contract_id,
        job_number=job_number,
        business_field=business_field,
        job_name=job_name,
        contract_amount=contract_amount,
        original_job_number=job_number,  # Store original values for deviation check
        original_job_name=job_name,
        original_contract_amount=contract_amount,
        created_by=current_user.id,
    )

    db.add(wip_entry)
    db.commit()
    db.refresh(wip_entry)

    return {
        "message": "WIP entry created successfully",
        "wip_entry_id": wip_entry.id,
        "has_deviations": False,  # New entries have no deviations initially
        "deviations": [],
    }


@router.put("/wip-entry/{wip_id}")
async def update_wip_entry(
    wip_id: int,
    update_data: WIPUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update WIP entry with automatic deviation detection
    """

    wip_entry = db.query(WIPEntry).filter(WIPEntry.id == wip_id).first()
    if not wip_entry:
        raise HTTPException(status_code=404, detail="WIP entry not found")

    # Update fields
    if update_data.job_number is not None:
        wip_entry.job_number = update_data.job_number
    if update_data.job_name is not None:
        wip_entry.job_name = update_data.job_name
    if update_data.contract_amount is not None:
        wip_entry.contract_amount = update_data.contract_amount
    if update_data.deviation_notes is not None:
        wip_entry.deviation_notes = update_data.deviation_notes

    # Check for deviations
    deviations = wip_entry.deviations
    wip_entry.has_deviations = len(deviations) > 0
    wip_entry.deviation_fields = json.dumps([d["field"] for d in deviations])
    wip_entry.last_deviation_check = datetime.utcnow()

    db.commit()
    db.refresh(wip_entry)

    return {
        "message": "WIP entry updated successfully",
        "wip_entry_id": wip_entry.id,
        "has_deviations": wip_entry.has_deviations,
        "deviations": deviations,
        "warning": (
            "This entry deviates from the original contract" if deviations else None
        ),
    }


class WIPUpdateRequest(BaseModel):
    job_number: Optional[str] = None
    business_field: Optional[str] = None
    job_name: Optional[str] = None
    contract_amount: Optional[Decimal] = None
    deviation_notes: Optional[str] = None
