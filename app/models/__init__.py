# app/models/__init__.py - Updated with correct naming
from app.models.company import Company
from app.models.user import User
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis
from app.models.contract_intelligence import ContractIntelligence  # Correct import

# Export all models
__all__ = ["Company", "User", "Contract", "ContractAnalysis", "ContractIntelligence"]
