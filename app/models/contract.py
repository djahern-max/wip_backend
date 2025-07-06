from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)

    # Simple extracted data
    contract_number = Column(String)
    contract_name = Column(String)
    contract_value = Column(Numeric(12, 2))

    # Store raw text for analysis
    raw_text = Column(Text)

    # Processing status
    is_processed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
