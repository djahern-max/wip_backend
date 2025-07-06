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
from sqlalchemy.ext.hybrid import hybrid_property
from app.core.database import Base
from app.services.encryption_service import encryption_service


class ContractAnalysis(Base):
    """
    AI-extracted contract data - comprehensive analysis results
    Now with encryption for sensitive fields
    """

    __tablename__ = "contract_analysis"  # Keep your existing table name

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    # Core Contract Information
    contract_number = Column(String)  # Keep as-is (often public)
    contract_name = Column(String)  # Keep original column
    contract_value = Column(Numeric(15, 2))  # Keep as-is (numbers less sensitive)

    # Contracting Parties - Original columns (will migrate to encrypted)
    contractor_name = Column(String)
    subcontractor_name = Column(String)
    owner_name = Column(String)

    # Key Dates
    agreement_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Project Details - Original columns
    project_location = Column(String)
    work_description = Column(Text)
    project_type = Column(String)

    # Financial Terms - Original columns
    payment_terms = Column(Text)
    retainage_percentage = Column(Numeric(5, 2))

    # Insurance & Bonding
    insurance_required = Column(Boolean, default=False)
    bond_required = Column(Boolean, default=False)
    insurance_amount = Column(Numeric(15, 2))
    bond_amount = Column(Numeric(15, 2))

    # Analysis Metadata
    ai_provider = Column(String, default="claude-3-sonnet")
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(Numeric(3, 2))  # 0.00 to 1.00

    # NEW: Encrypted columns (will be added by migration)
    contractor_name_encrypted = Column(String)
    subcontractor_name_encrypted = Column(String)
    owner_name_encrypted = Column(String)
    contract_name_encrypted = Column(String)
    project_location_encrypted = Column(String)
    work_description_encrypted = Column(Text)
    payment_terms_encrypted = Column(Text)
    insurance_amount_encrypted = Column(String)
    bond_amount_encrypted = Column(String)

    # Relationship
    contract = relationship("Contract", backref="analysis")

    # Utility methods for encryption migration
    def encrypt_sensitive_data(self):
        """
        Migrate existing plain text data to encrypted fields
        Call this method during data migration
        """
        if self.contractor_name and not self.contractor_name_encrypted:
            self.contractor_name_encrypted = encryption_service.encrypt_text(
                self.contractor_name
            )

        if self.subcontractor_name and not self.subcontractor_name_encrypted:
            self.subcontractor_name_encrypted = encryption_service.encrypt_text(
                self.subcontractor_name
            )

        if self.owner_name and not self.owner_name_encrypted:
            self.owner_name_encrypted = encryption_service.encrypt_text(self.owner_name)

        if self.contract_name and not self.contract_name_encrypted:
            self.contract_name_encrypted = encryption_service.encrypt_text(
                self.contract_name
            )

        if self.project_location and not self.project_location_encrypted:
            self.project_location_encrypted = encryption_service.encrypt_text(
                self.project_location
            )

        if self.work_description and not self.work_description_encrypted:
            self.work_description_encrypted = encryption_service.encrypt_text(
                self.work_description
            )

        if self.payment_terms and not self.payment_terms_encrypted:
            self.payment_terms_encrypted = encryption_service.encrypt_text(
                self.payment_terms
            )

        if self.insurance_amount and not self.insurance_amount_encrypted:
            self.insurance_amount_encrypted = encryption_service.encrypt_text(
                str(self.insurance_amount)
            )

        if self.bond_amount and not self.bond_amount_encrypted:
            self.bond_amount_encrypted = encryption_service.encrypt_text(
                str(self.bond_amount)
            )

    # Helper methods to get decrypted data (for reading)
    def get_contractor_name_secure(self):
        """Get contractor name from encrypted field if available, fallback to plain"""
        if self.contractor_name_encrypted:
            return encryption_service.decrypt_text(self.contractor_name_encrypted)
        return self.contractor_name

    def get_subcontractor_name_secure(self):
        """Get subcontractor name from encrypted field if available, fallback to plain"""
        if self.subcontractor_name_encrypted:
            return encryption_service.decrypt_text(self.subcontractor_name_encrypted)
        return self.subcontractor_name

    def get_owner_name_secure(self):
        """Get owner name from encrypted field if available, fallback to plain"""
        if self.owner_name_encrypted:
            return encryption_service.decrypt_text(self.owner_name_encrypted)
        return self.owner_name

    def get_contract_name_secure(self):
        """Get contract name from encrypted field if available, fallback to plain"""
        if self.contract_name_encrypted:
            return encryption_service.decrypt_text(self.contract_name_encrypted)
        return self.contract_name

    def get_project_location_secure(self):
        """Get project location from encrypted field if available, fallback to plain"""
        if self.project_location_encrypted:
            return encryption_service.decrypt_text(self.project_location_encrypted)
        return self.project_location

    def get_work_description_secure(self):
        """Get work description from encrypted field if available, fallback to plain"""
        if self.work_description_encrypted:
            return encryption_service.decrypt_text(self.work_description_encrypted)
        return self.work_description

    def get_payment_terms_secure(self):
        """Get payment terms from encrypted field if available, fallback to plain"""
        if self.payment_terms_encrypted:
            return encryption_service.decrypt_text(self.payment_terms_encrypted)
        return self.payment_terms

    def get_insurance_amount_secure(self):
        """Get insurance amount from encrypted field if available, fallback to plain"""
        if self.insurance_amount_encrypted:
            try:
                from decimal import Decimal

                decrypted = encryption_service.decrypt_text(
                    self.insurance_amount_encrypted
                )
                return Decimal(decrypted) if decrypted else None
            except:
                return None
        return self.insurance_amount

    def get_bond_amount_secure(self):
        """Get bond amount from encrypted field if available, fallback to plain"""
        if self.bond_amount_encrypted:
            try:
                from decimal import Decimal

                decrypted = encryption_service.decrypt_text(self.bond_amount_encrypted)
                return Decimal(decrypted) if decrypted else None
            except:
                return None
        return self.bond_amount

    # Helper methods for setting encrypted data (for new records)
    def set_contractor_name_secure(self, value):
        """Set contractor name in encrypted field"""
        if value:
            self.contractor_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.contractor_name_encrypted = None

    def set_subcontractor_name_secure(self, value):
        """Set subcontractor name in encrypted field"""
        if value:
            self.subcontractor_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.subcontractor_name_encrypted = None

    def set_owner_name_secure(self, value):
        """Set owner name in encrypted field"""
        if value:
            self.owner_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.owner_name_encrypted = None

    def set_contract_name_secure(self, value):
        """Set contract name in encrypted field"""
        if value:
            self.contract_name_encrypted = encryption_service.encrypt_text(value)
        else:
            self.contract_name_encrypted = None

    def set_project_location_secure(self, value):
        """Set project location in encrypted field"""
        if value:
            self.project_location_encrypted = encryption_service.encrypt_text(value)
        else:
            self.project_location_encrypted = None

    def set_work_description_secure(self, value):
        """Set work description in encrypted field"""
        if value:
            self.work_description_encrypted = encryption_service.encrypt_text(value)
        else:
            self.work_description_encrypted = None

    def set_payment_terms_secure(self, value):
        """Set payment terms in encrypted field"""
        if value:
            self.payment_terms_encrypted = encryption_service.encrypt_text(value)
        else:
            self.payment_terms_encrypted = None

    def set_insurance_amount_secure(self, value):
        """Set insurance amount in encrypted field"""
        if value is not None:
            self.insurance_amount_encrypted = encryption_service.encrypt_text(
                str(value)
            )
        else:
            self.insurance_amount_encrypted = None

    def set_bond_amount_secure(self, value):
        """Set bond amount in encrypted field"""
        if value is not None:
            self.bond_amount_encrypted = encryption_service.encrypt_text(str(value))
        else:
            self.bond_amount_encrypted = None
