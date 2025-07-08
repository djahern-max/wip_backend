# app/models/directories.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Float,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import json


class ContractIntelligence(Base):
    """
    Store AI classification results for contracts
    Enables fast retrieval and caching of document intelligence
    """

    __tablename__ = "contract_intelligence"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(
        Integer, ForeignKey("contracts.id"), nullable=False, index=True
    )

    # Classification results
    document_type = Column(String(50))  # PRIMARY_CONTRACT, CHANGE_ORDER, etc.
    importance = Column(String(20), index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(30))  # EXECUTED_SIGNED, DRAFT_UNSIGNED, etc.
    importance_score = Column(Float)  # Calculated ranking score
    is_main_contract = Column(Boolean, default=False, index=True)
    confidence = Column(String(20))  # HIGH, MEDIUM, LOW

    # Extracted information (non-sensitive)
    main_parties = Column(Text)  # JSON array of company names
    contract_value_text = Column(String)  # As extracted from text
    project_info = Column(Text)  # Brief project description
    summary = Column(Text)  # One-line summary
    recommendation = Column(String(30))  # ANALYZE_FULLY, REVIEW_MANUALLY, etc.

    # Full classification data (JSON blob for flexibility)
    classification_data = Column(Text)  # Complete classification result as JSON

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    contract = relationship("Contract", back_populates="intelligence")

    @property
    def main_parties_list(self):
        """Get main parties as a list"""
        if self.main_parties:
            try:
                return json.loads(self.main_parties)
            except:
                return []
        return []

    @main_parties_list.setter
    def main_parties_list(self, value):
        """Set main parties from a list"""
        if value:
            self.main_parties = json.dumps(value)
        else:
            self.main_parties = None

    @property
    def full_classification(self):
        """Get full classification data as dict"""
        if self.classification_data:
            try:
                return json.loads(self.classification_data)
            except:
                return {}
        return {}

    @full_classification.setter
    def full_classification(self, value):
        """Set full classification data from dict"""
        if value:
            self.classification_data = json.dumps(value)
        else:
            self.classification_data = None
