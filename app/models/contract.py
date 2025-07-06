# app/models/contract.py - Remove circular import
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
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

    # Metadata (safe to store in plain text)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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
