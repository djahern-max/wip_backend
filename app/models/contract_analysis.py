# app/models/contract_analysis.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ContractAnalysis(Base):
    """
    AI-extracted contract data - comprehensive analysis results
    """

    __tablename__ = "contract_analyses"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    # Core Contract Information
    contract_number = Column(String)  # CTDOT #172-517
    contract_name = Column(String)  # Project title/description
    contract_value = Column(Numeric(15, 2))  # Total dollar amount

    # Contracting Parties
    contractor_name = Column(String)  # Main contractor
    subcontractor_name = Column(String)  # Subcontractor (if applicable)
    owner_name = Column(String)  # Project owner/client

    # Key Dates
    agreement_date = Column(DateTime)  # Contract signing date
    start_date = Column(DateTime)  # Work start date
    end_date = Column(DateTime)  # Work completion date

    # Project Details
    project_location = Column(String)  # Where work is performed
    work_description = Column(Text)  # Detailed scope of work
    project_type = Column(String)  # Bridge, road, building, etc.

    # Financial Terms
    payment_terms = Column(Text)  # Payment schedule/terms
    retainage_percentage = Column(Numeric(5, 2))  # Retainage %

    # Insurance & Bonding
    insurance_required = Column(Boolean, default=False)
    bond_required = Column(Boolean, default=False)
    insurance_amount = Column(Numeric(15, 2))
    bond_amount = Column(Numeric(15, 2))

    # Analysis Metadata
    ai_provider = Column(String, default="claude-3-sonnet")
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(Numeric(3, 2))  # 0.00 to 1.00

    # Relationship
    contract = relationship("Contract", backref="analysis")
