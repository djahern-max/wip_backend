# ===== backend/app/models/wip.py =====
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class WIP(Base):
    __tablename__ = "wip"

    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(50), nullable=False, index=True)
    project_name = Column(String(200), nullable=False)

    # Add user association
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="wip_items")
