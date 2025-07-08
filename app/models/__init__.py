# app/models/__init__.py - Updated with WIPEntry
from app.models.company import Company
from app.models.user import User
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis
from models.directories import ContractIntelligence
from app.models.wip_entry import WIPEntry  # Added WIPEntry import

# Export all models
__all__ = [
    "Company",
    "User",
    "Contract",
    "ContractAnalysis",
    "ContractIntelligence",
    "WIPEntry",
]
