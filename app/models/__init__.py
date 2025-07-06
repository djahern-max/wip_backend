# app/models/__init__.py
"""
Model imports for the WIP Backend application
Import all models here to ensure they are registered with SQLAlchemy
"""

from app.models.company import Company
from app.models.user import User
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis

# Export all models
__all__ = ["Company", "User", "Contract", "ContractAnalysis"]
