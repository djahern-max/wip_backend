# app/models/__init__.py - Updated with Directories model
from app.models.company import Company
from app.models.user import User
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis
from app.models.directories import Directories
from app.models.wip_entry import WIPEntry

# Export all models
__all__ = [
    "Company",
    "User",
    "Contract",
    "ContractAnalysis",
    "Directories",
    "WIPEntry",
]
