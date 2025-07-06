# app/models/contract_analysis.py - Fixed relationships
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
from sqlalchemy.ext.hybrid import hybrid_property
from app.core.database import Base
from app.services.encryption_service import encryption_service


class ContractAnalysis(Base):
    """
    AI-extracted contract data - ENCRYPTION FIRST ARCHITECTURE
    Only sensitive data is encrypted, non-sensitive data in plain text
    """

    __tablename__ = "contract_analysis"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    # Company association (nullable for MVP compatibility)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # NON-SENSITIVE DATA (safe in plain text)
    contract_number = Column(String)  # Often public reference numbers
    contract_value = Column(Numeric(15, 2))  # Dollar amounts are less sensitive
    agreement_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    project_type = Column(String)  # Generic categories (bridge, road, etc.)
    retainage_percentage = Column(Numeric(5, 2))
    insurance_required = Column(Boolean, default=False)
    bond_required = Column(Boolean, default=False)
    ai_provider = Column(String, default="claude-3-sonnet")
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(Numeric(3, 2))

    # SENSITIVE DATA - ENCRYPTED ONLY (no plain text columns)
    contractor_name_encrypted = Column(String)
    subcontractor_name_encrypted = Column(String)
    owner_name_encrypted = Column(String)
    contract_name_encrypted = Column(String)
    project_location_encrypted = Column(String)
    work_description_encrypted = Column(Text)
    payment_terms_encrypted = Column(Text)
    insurance_amount_encrypted = Column(String)
    bond_amount_encrypted = Column(String)

    # Relationships
    contract = relationship("Contract", back_populates="analysis")
    company = relationship("Company")

    # AUTOMATIC ENCRYPTION PROPERTIES
    @hybrid_property
    def contractor_name(self):
        """Automatically decrypt contractor name"""
        if self.contractor_name_encrypted:
            return encryption_service.decrypt_text(self.contractor_name_encrypted)
        return None

    @contractor_name.setter
    def contractor_name(self, value):
        """Automatically encrypt contractor name"""
        if value:
            self.contractor_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.contractor_name_encrypted = None

    @hybrid_property
    def subcontractor_name(self):
        if self.subcontractor_name_encrypted:
            return encryption_service.decrypt_text(self.subcontractor_name_encrypted)
        return None

    @subcontractor_name.setter
    def subcontractor_name(self, value):
        if value:
            self.subcontractor_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.subcontractor_name_encrypted = None

    @hybrid_property
    def owner_name(self):
        if self.owner_name_encrypted:
            return encryption_service.decrypt_text(self.owner_name_encrypted)
        return None

    @owner_name.setter
    def owner_name(self, value):
        if value:
            self.owner_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.owner_name_encrypted = None

    @hybrid_property
    def contract_name(self):
        if self.contract_name_encrypted:
            return encryption_service.decrypt_text(self.contract_name_encrypted)
        return None

    @contract_name.setter
    def contract_name(self, value):
        if value:
            self.contract_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.contract_name_encrypted = None

    @hybrid_property
    def project_location(self):
        if self.project_location_encrypted:
            return encryption_service.decrypt_text(self.project_location_encrypted)
        return None

    @project_location.setter
    def project_location(self, value):
        if value:
            self.project_location_encrypted = encryption_service.encrypt_text(value)
        else:
            self.project_location_encrypted = None

    @hybrid_property
    def work_description(self):
        if self.work_description_encrypted:
            return encryption_service.decrypt_text(self.work_description_encrypted)
        return None

    @work_description.setter
    def work_description(self, value):
        if value:
            self.work_description_encrypted = encryption_service.encrypt_text(value)
        else:
            self.work_description_encrypted = None

    @hybrid_property
    def payment_terms(self):
        if self.payment_terms_encrypted:
            return encryption_service.decrypt_text(self.payment_terms_encrypted)
        return None

    @payment_terms.setter
    def payment_terms(self, value):
        if value:
            self.payment_terms_encrypted = encryption_service.encrypt_text(value)
        else:
            self.payment_terms_encrypted = None

    @hybrid_property
    def insurance_amount(self):
        if self.insurance_amount_encrypted:
            try:
                from decimal import Decimal

                decrypted = encryption_service.decrypt_text(
                    self.insurance_amount_encrypted
                )
                return Decimal(decrypted) if decrypted else None
            except:
                return None
        return None

    @insurance_amount.setter
    def insurance_amount(self, value):
        if value is not None:
            self.insurance_amount_encrypted = encryption_service.encrypt_text(
                str(value)
            )
        else:
            self.insurance_amount_encrypted = None

    @hybrid_property
    def bond_amount(self):
        if self.bond_amount_encrypted:
            try:
                from decimal import Decimal

                decrypted = encryption_service.decrypt_text(self.bond_amount_encrypted)
                return Decimal(decrypted) if decrypted else None
            except:
                return None
        return None

    @bond_amount.setter
    def bond_amount(self, value):
        if value is not None:
            self.bond_amount_encrypted = encryption_service.encrypt_text(str(value))
        else:
            self.bond_amount_encrypted = None
