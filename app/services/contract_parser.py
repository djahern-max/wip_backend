from .ai_contract_analyzer import AIContractAnalyzer


def parse_contract_data(text: str) -> dict:
    """Ask direct questions about the contract - NO STRUCTURED EXTRACTION"""

    analyzer = AIContractAnalyzer()

    # Get direct answers
    contract_value_answer = analyzer.get_contract_value(text)
    contract_number_answer = analyzer.get_contract_number(text)

    return {
        "contract_value_raw": contract_value_answer,
        "contract_number_raw": contract_number_answer,
        "analysis_type": "direct_questioning",
    }
