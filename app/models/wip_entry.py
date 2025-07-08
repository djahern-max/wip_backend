# app/models/wip_entry.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    Text,
    Decimal,
    func,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class WIPEntry(Base):
    __tablename__ = "wip_entries"

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), unique=True)

    # Editable WIP fields
    job_number = Column(String)
    business_field = Column(String)
    job_name = Column(String)
    contract_amount = Column(Decimal)

    # Original contract values (for deviation comparison)
    original_job_number = Column(String)
    original_job_name = Column(String)
    original_contract_amount = Column(Decimal)

    # Deviation tracking
    has_deviations = Column(Boolean, default=False)
    deviation_fields = Column(Text)  # JSON array of fields that deviate
    deviation_notes = Column(Text)  # User explanation for deviations

    status = Column(String, default="ACTIVE")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_deviation_check = Column(DateTime)

    @property
    def deviations(self):
        """Get current deviations from contract"""
        deviations = []

        if self.job_number != self.original_job_number:
            deviations.append(
                {
                    "field": "job_number",
                    "field_label": "Job Number",
                    "contract_value": self.original_job_number,
                    "wip_value": self.job_number,
                    "severity": "medium",
                }
            )

        if self.job_name != self.original_job_name:
            deviations.append(
                {
                    "field": "job_name",
                    "field_label": "Job Name",
                    "contract_value": self.original_job_name,
                    "wip_value": self.job_name,
                    "severity": "low",
                }
            )

        if self.contract_amount != self.original_contract_amount:
            deviations.append(
                {
                    "field": "contract_amount",
                    "field_label": "Contract Amount",
                    "contract_value": str(self.original_contract_amount),
                    "wip_value": str(self.contract_amount),
                    "severity": "high",  # Amount changes are critical
                }
            )

        return deviations
