from typing import Dict, Optional
from decimal import Decimal
import re
from .ai_contract_analyzer import AIContractAnalyzer


def parse_contract_data(text: str) -> Dict[str, Optional[str]]:
    """Parse contract data using AI analysis"""
    
    # Initialize AI analyzer
    analyzer = AIContractAnalyzer()
    
    # Use AI to extract data
    ai_result = analyzer.analyze_contract(text)
    
    # Process the contract value to ensure it's a proper Decimal
    contract_value = ai_result.get("contract_value")
    if contract_value:
        try:
            # Extract numeric value and convert to Decimal
            if isinstance(contract_value, str):
                # Remove currency symbols and commas
                numeric_value = re.sub(r'[^\d.]', '', contract_value)
                if numeric_value:
                    contract_value = Decimal(numeric_value)
                else:
                    contract_value = None
            elif isinstance(contract_value, (int, float)):
                contract_value = Decimal(str(contract_value))
        except:
            contract_value = None
    
    return {
        "contract_number": ai_result.get("contract_number"),
        "contract_name": ai_result.get("contract_name"),
        "contract_value": contract_value,
        "contractor_name": ai_result.get("contractor_name"),
        "subcontractor_name": ai_result.get("subcontractor_name"),
        "project_location": ai_result.get("project_location"),
        "work_description": ai_result.get("work_description"),
        "start_date": ai_result.get("start_date"),
        "end_date": ai_result.get("end_date")
    }
