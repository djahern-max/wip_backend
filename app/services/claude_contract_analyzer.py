import requests
import re
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from app.core.config import settings


class ComprehensiveClaudeAnalyzer:
    """
    Comprehensive contract analyzer - extracts 15+ fields in one API call
    Cost: ~$0.08-0.12 per contract (one-time analysis)
    """

    def __init__(self):
        if not settings.anthropic_api_key:
            raise Exception("Anthropic API key not configured")

        self.api_key = settings.anthropic_api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

    def _ask_claude(self, prompt: str, max_tokens: int = 800) -> str:
        """Send prompt to Claude and return response"""

        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(
            self.base_url, headers=self.headers, json=data, timeout=60
        )

        if response.status_code != 200:
            raise Exception(
                f"Claude API error: {response.status_code} - {response.text}"
            )

        result = response.json()
        return result["content"][0]["text"].strip()

    def extract_comprehensive_data(self, contract_text: str) -> Dict[str, Any]:
        """
        Extract all contract data in one comprehensive API call
        Returns data ready for ContractAnalysis table
        """

        prompt = f"""
        Analyze this contract and extract the following information. If any field cannot be found, use "NOT_FOUND".
        
        Format your response EXACTLY like this structure:
        
        CONTRACT_NUMBER: [contract/project number, CTDOT numbers, etc.]
        CONTRACT_NAME: [project title or main work description]
        CONTRACT_VALUE: [total dollar amount as number only, no commas]
        CONTRACTOR_NAME: [main contractor company name]
        SUBCONTRACTOR_NAME: [subcontractor company name if applicable]
        OWNER_NAME: [project owner/client organization]
        AGREEMENT_DATE: [contract signing date in YYYY-MM-DD format]
        START_DATE: [project start date in YYYY-MM-DD format]
        END_DATE: [project completion date in YYYY-MM-DD format]
        PROJECT_LOCATION: [where work is being performed]
        WORK_DESCRIPTION: [detailed scope of work, keep under 500 chars]
        PROJECT_TYPE: [type of project: bridge, road, building, etc.]
        PAYMENT_TERMS: [payment schedule or terms, keep under 300 chars]
        RETAINAGE_PERCENTAGE: [retainage percentage as decimal, e.g. 10 for 10%]
        INSURANCE_REQUIRED: [YES or NO]
        BOND_REQUIRED: [YES or NO]
        INSURANCE_AMOUNT: [insurance amount as number only]
        BOND_AMOUNT: [bond amount as number only]
        
        Examples:
        CONTRACT_NUMBER: 172-517
        CONTRACT_VALUE: 1582389
        AGREEMENT_DATE: 2023-09-19
        INSURANCE_REQUIRED: YES
        
        CONTRACT TEXT:
        {contract_text}
        """

        try:
            response = self._ask_claude(prompt, max_tokens=1000)
            return self._parse_comprehensive_response(response)

        except Exception as e:
            print(f"Comprehensive extraction failed: {e}")
            raise Exception(f"Contract analysis failed: {str(e)}")

    def _parse_comprehensive_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's structured response into database-ready format"""

        data = {
            "contract_number": None,
            "contract_name": None,
            "contract_value": None,
            "contractor_name": None,
            "subcontractor_name": None,
            "owner_name": None,
            "agreement_date": None,
            "start_date": None,
            "end_date": None,
            "project_location": None,
            "work_description": None,
            "project_type": None,
            "payment_terms": None,
            "retainage_percentage": None,
            "insurance_required": False,
            "bond_required": False,
            "insurance_amount": None,
            "bond_amount": None,
            "ai_provider": "claude-3-sonnet",
            "confidence_score": Decimal("0.85"),  # Default confidence
        }

        # Parse each line of the response
        for line in response.split("\n"):
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().upper()
            value = value.strip()

            if value == "NOT_FOUND" or not value:
                continue

            # Map and clean each field
            if "CONTRACT_NUMBER" in key:
                data["contract_number"] = self._clean_contract_number(value)

            elif "CONTRACT_NAME" in key:
                data["contract_name"] = value[:255]  # Limit length

            elif "CONTRACT_VALUE" in key:
                data["contract_value"] = self._extract_decimal(value)

            elif "CONTRACTOR_NAME" in key:
                data["contractor_name"] = value[:255]

            elif "SUBCONTRACTOR_NAME" in key:
                data["subcontractor_name"] = value[:255]

            elif "OWNER_NAME" in key:
                data["owner_name"] = value[:255]

            elif "AGREEMENT_DATE" in key:
                data["agreement_date"] = self._parse_date(value)

            elif "START_DATE" in key:
                data["start_date"] = self._parse_date(value)

            elif "END_DATE" in key:
                data["end_date"] = self._parse_date(value)

            elif "PROJECT_LOCATION" in key:
                data["project_location"] = value[:255]

            elif "WORK_DESCRIPTION" in key:
                data["work_description"] = value[:500]

            elif "PROJECT_TYPE" in key:
                data["project_type"] = value[:100]

            elif "PAYMENT_TERMS" in key:
                data["payment_terms"] = value[:300]

            elif "RETAINAGE_PERCENTAGE" in key:
                data["retainage_percentage"] = self._extract_decimal(value)

            elif "INSURANCE_REQUIRED" in key:
                data["insurance_required"] = value.upper() == "YES"

            elif "BOND_REQUIRED" in key:
                data["bond_required"] = value.upper() == "YES"

            elif "INSURANCE_AMOUNT" in key:
                data["insurance_amount"] = self._extract_decimal(value)

            elif "BOND_AMOUNT" in key:
                data["bond_amount"] = self._extract_decimal(value)

        return data

    def _clean_contract_number(self, value: str) -> str:
        """Clean contract number format"""
        clean = value.replace("CTDOT #", "").replace("CTDOT", "").strip()
        clean = re.sub(r"^[#\s]+", "", clean)
        return clean[:50] if clean else None

    def _extract_decimal(self, value: str) -> Optional[Decimal]:
        """Extract decimal number from string"""
        try:
            numbers = re.findall(r"[\d.]+", value.replace(",", ""))
            if numbers:
                return Decimal(numbers[0])
        except:
            pass
        return None

    def _parse_date(self, value: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        try:
            # Try YYYY-MM-DD format first
            if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                return datetime.strptime(value, "%Y-%m-%d")

            # Try other common formats
            for fmt in ["%B %d, %Y", "%m/%d/%Y", "%m-%d-%Y"]:
                try:
                    return datetime.strptime(value, fmt)
                except:
                    continue
        except:
            pass
        return None

    def analyze_contract(self, contract_text: str) -> Dict[str, Any]:
        """
        Main method: Comprehensive contract analysis
        Returns all extracted data ready for database storage
        """

        if not contract_text or len(contract_text.strip()) < 100:
            raise Exception("Contract text too short or empty")

        # Extract all data in one call
        extracted_data = self.extract_comprehensive_data(contract_text)

        # Add metadata
        extracted_data.update(
            {"analysis_date": datetime.utcnow(), "text_length": len(contract_text)}
        )

        return {
            "success": True,
            "data": extracted_data,
            "fields_extracted": sum(
                1 for v in extracted_data.values() if v is not None
            ),
            "total_possible_fields": 18,
        }
