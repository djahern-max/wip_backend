# app/models/contract.py
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
    Contract storage - encryption-first architecture
    """

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)

    # ONLY encrypted storage - no plain text
    raw_text_encrypted = Column(Text, nullable=False)

    # Future-ready fields (nullable for MVP compatibility)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    job_number = Column(String(100), nullable=True)
    job_name = Column(String(255), nullable=True)

    # Metadata (safe to store in plain text)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    company = relationship("Company", back_populates="contracts")
    analysis = relationship(
        "ContractAnalysis", back_populates="contract", uselist=False
    )

    # Indexes for performance
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
