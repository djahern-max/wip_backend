# app/models/company.py - NEW model for multi-tenant support
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Company(Base):
    """
    Company/Organization model for multi-tenant support
    """

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    subscription_plan = Column(String, default="basic")  # basic, pro, enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    users = relationship("User", back_populates="company")
    contracts = relationship("Contract", back_populates="company")


# app/models/user.py - Updated with company support
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # NEW: Company association (nullable for MVP compatibility)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    company = relationship("Company", back_populates="users")


# app/models/contract.py - Updated with company and job support
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.services.encryption_service import encryption_service


class Contract(Base):
    """
    Contract storage - encryption-first architecture with job support
    """

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)

    # ONLY encrypted storage - no plain text
    raw_text_encrypted = Column(Text, nullable=False)

    # NEW: Future-ready fields (optional for MVP)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    job_number = Column(String(100), nullable=True)  # Flexible length for any format
    job_name = Column(String(255), nullable=True)

    # Metadata (safe to store in plain text)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    company = relationship("Company", back_populates="contracts")
    analysis = relationship(
        "ContractAnalysis", back_populates="contract", uselist=False
    )

    # Indexes for future job grouping and company separation
    __table_args__ = (
        Index("idx_company_job", "company_id", "job_number"),
        Index("idx_company_created", "company_id", "created_at"),
    )

    @hybrid_property
    def raw_text(self):
        """Get decrypted raw text"""
        if self.raw_text_encrypted:
            return encryption_service.decrypt_text(self.raw_text_encrypted)
        return None

    @raw_text.setter
    def raw_text(self, value):
        """Set encrypted raw text"""
        if value:
            self.raw_text_encrypted = encryption_service.encrypt_text(value)
        else:
            self.raw_text_encrypted = None

    @property
    def display_job_identifier(self):
        """Get job identifier for display (job_number or auto-generated)"""
        if self.job_number:
            return self.job_number
        return f"CONTRACT-{self.id}"

    @property
    def display_job_name(self):
        """Get job name for display (job_name or filename)"""
        if self.job_name:
            return self.job_name
        return self.filename.replace(".pdf", "").replace("_", " ")


# app/models/contract_analysis.py - Updated with company support
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
    AI-extracted contract data - ENCRYPTION FIRST ARCHITECTURE with company support
    """

    __tablename__ = "contract_analysis"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    # NEW: Company association (for multi-tenant queries)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # NON-SENSITIVE DATA (safe in plain text)
    contract_number = Column(String)
    contract_value = Column(Numeric(15, 2))
    agreement_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    project_type = Column(String)
    retainage_percentage = Column(Numeric(5, 2))
    insurance_required = Column(Boolean, default=False)
    bond_required = Column(Boolean, default=False)
    ai_provider = Column(String, default="claude-3-sonnet")
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(Numeric(3, 2))

    # SENSITIVE DATA - ENCRYPTED ONLY
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
        if self.contractor_name_encrypted:
            return encryption_service.decrypt_text(self.contractor_name_encrypted)
        return None

    @contractor_name.setter
    def contractor_name(self, value):
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
