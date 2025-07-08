import requests
import re
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from app.core.config import settings


class SimplifiedContractAnalyzer:
    """
    Simplified contract analyzer - extracts key fields only
    Fast, reliable, and cost-effective for main contract analysis
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

    def _ask_claude(self, prompt: str, max_tokens: int = 600) -> str:
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

    def extract_key_contract_data(self, contract_text: str) -> Dict[str, Any]:
        """
        Extract key contract information for database storage
        """

        # Use first 8000 characters for analysis (faster and cheaper)
        text_sample = contract_text[:8000]

        prompt = f"""
        Analyze this construction contract and extract key information. If any field cannot be found, use "NOT_FOUND".
        
        Please respond in this EXACT format:
        
        CONTRACT_NUMBER: [contract/project number]
        CONTRACT_NAME: [project title/name]
        CONTRACT_VALUE: [total dollar amount as number only, no $ or commas]
        CONTRACTOR_NAME: [main contractor company name]
        OWNER_NAME: [client/owner organization name]
        PROJECT_LOCATION: [project location/address]
        PROJECT_TYPE: [type: bridge, road, building, etc.]
        AGREEMENT_DATE: [contract date in YYYY-MM-DD format if found]
        WORK_DESCRIPTION: [brief description of work scope]
        
        CONTRACT TEXT:
        {text_sample}
        """

        try:
            response = self._ask_claude(prompt, max_tokens=500)
            return self._parse_response(response)

        except Exception as e:
            print(f"Contract analysis failed: {e}")
            raise Exception(f"Failed to analyze contract: {str(e)}")

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's response into database-ready format"""

        data = {
            "contract_number": None,
            "contract_name": None,
            "contract_value": None,
            "contractor_name": None,
            "owner_name": None,
            "project_location": None,
            "project_type": None,
            "agreement_date": None,
            "work_description": None,
            "ai_provider": "claude-3-sonnet",
            "confidence_score": Decimal("0.80"),  # Conservative estimate
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
                data["contract_number"] = self._clean_text(value, 50)

            elif "CONTRACT_NAME" in key:
                data["contract_name"] = self._clean_text(value, 255)

            elif "CONTRACT_VALUE" in key:
                data["contract_value"] = self._extract_decimal(value)

            elif "CONTRACTOR_NAME" in key:
                data["contractor_name"] = self._clean_text(value, 255)

            elif "OWNER_NAME" in key:
                data["owner_name"] = self._clean_text(value, 255)

            elif "PROJECT_LOCATION" in key:
                data["project_location"] = self._clean_text(value, 255)

            elif "PROJECT_TYPE" in key:
                data["project_type"] = self._clean_text(value, 100)

            elif "AGREEMENT_DATE" in key:
                data["agreement_date"] = self._parse_date(value)

            elif "WORK_DESCRIPTION" in key:
                data["work_description"] = self._clean_text(value, 500)

        return data

    def _clean_text(self, value: str, max_length: int) -> Optional[str]:
        """Clean and limit text length"""
        if not value or value == "NOT_FOUND":
            return None

        # Clean up common contract artifacts
        clean = value.replace("CTDOT #", "").replace("CTDOT", "").strip()
        clean = re.sub(r"^[#\s]+", "", clean)

        return clean[:max_length] if clean else None

    def _extract_decimal(self, value: str) -> Optional[Decimal]:
        """Extract decimal number from string"""
        try:
            # Remove commas, dollar signs, and extract numbers
            clean_value = re.sub(r"[,$]", "", value)
            numbers = re.findall(r"\d+\.?\d*", clean_value)
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
        Main method: Extract key contract data for database storage
        """

        if not contract_text or len(contract_text.strip()) < 100:
            raise Exception("Contract text too short or empty")

        # Extract key data
        extracted_data = self.extract_key_contract_data(contract_text)

        # Add metadata
        extracted_data.update(
            {"analysis_date": datetime.utcnow(), "text_length": len(contract_text)}
        )

        # Count successful extractions
        fields_extracted = sum(
            1 for v in extracted_data.values() if v is not None and v != "NOT_FOUND"
        )

        return {
            "success": True,
            "data": extracted_data,
            "fields_extracted": fields_extracted,
            "total_possible_fields": 9,  # Key fields only
            "summary": self._generate_summary(extracted_data),
        }

    def _generate_summary(self, data: Dict[str, Any]) -> str:
        """Generate a human-readable summary"""

        contract_name = data.get("contract_name", "Unknown Project")
        contractor = data.get("contractor_name", "Unknown Contractor")
        value = data.get("contract_value")

        summary_parts = [f"Contract: {contract_name}"]

        if contractor:
            summary_parts.append(f"Contractor: {contractor}")

        if value:
            summary_parts.append(f"Value: ${value:,.2f}")

        return " | ".join(summary_parts)
