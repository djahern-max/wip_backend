# app/models/contract.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from app.core.database import Base


class Contract(Base):
    """
    Simplified contract storage - with optional encryption support
    """

    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    raw_text = Column(Text)  # Keep as plain text for now
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Optional: Add encrypted column for future use
    raw_text_encrypted = Column(Text)

    def get_raw_text_secure(self):
        """
        Get raw text with encryption support (future-ready)
        For now, just returns the plain text
        """
        # Priority: encrypted field first, then fallback to plain
        if self.raw_text_encrypted:
            try:
                from app.services.encryption_service import encryption_service

                return encryption_service.decrypt_text(self.raw_text_encrypted)
            except Exception as e:
                print(f"Decryption failed, using plain text: {e}")
                return self.raw_text

        # Fallback to plain text
        return self.raw_text

    def set_raw_text_secure(self, value):
        """
        Set raw text with optional encryption
        For now, stores in plain text
        """
        self.raw_text = value

        # Optional: Also store encrypted version
        try:
            from app.services.encryption_service import encryption_service

            if value:
                self.raw_text_encrypted = encryption_service.encrypt_text(value)
        except Exception as e:
            print(f"Encryption failed, storing plain text only: {e}")
            # Continue without encryption if it fails

    def migrate_to_encrypted(self):
        """
        Migrate existing plain text to encrypted field
        Call this during data migration
        """
        if self.raw_text and not self.raw_text_encrypted:
            try:
                from app.services.encryption_service import encryption_service

                self.raw_text_encrypted = encryption_service.encrypt_text(self.raw_text)
                return True
            except Exception as e:
                print(f"Migration encryption failed for contract {self.id}: {e}")
                return False
        return False
