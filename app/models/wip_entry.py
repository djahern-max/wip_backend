# app/models/wip_entry.py - Ultra simplified version
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Numeric,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class WIPEntry(Base):
    __tablename__ = "wip_entries"

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), unique=True)

    # Just the 3 business fields
    job_number = Column(String)
    job_name = Column(String)
    contract_amount = Column(Numeric(15, 2))

    # Relationships
    contract = relationship("Contract", back_populates="wip_entry")
