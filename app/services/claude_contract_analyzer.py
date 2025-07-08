import requests
import time
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from app.core.config import settings
import re


class ComprehensiveClaudeAnalyzer:
    """
    Comprehensive contract analyzer with retry logic for 529 errors
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

    def _ask_claude(
        self, prompt: str, max_tokens: int = 800, max_retries: int = 3
    ) -> str:
        """Send prompt to Claude with retry logic for 529 errors"""

        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    self.base_url, headers=self.headers, json=data, timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["content"][0]["text"].strip()

                elif response.status_code == 529:
                    # Overloaded error - wait and retry
                    if attempt < max_retries:
                        wait_time = (
                            2**attempt
                        ) * 5  # Exponential backoff: 5s, 10s, 20s
                        print(
                            f"Claude API overloaded (529). Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            f"Claude API overloaded after {max_retries + 1} attempts. Please try again later."
                        )

                elif response.status_code == 429:
                    # Rate limit - wait longer
                    if attempt < max_retries:
                        wait_time = 30 + (attempt * 10)  # 30s, 40s, 50s
                        print(
                            f"Claude API rate limited (429). Waiting {wait_time}s... (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(
                            f"Claude API rate limited after {max_retries + 1} attempts."
                        )

                else:
                    # Other error - don't retry
                    raise Exception(
                        f"Claude API error: {response.status_code} - {response.text}"
                    )

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(
                        f"Request timeout. Retrying... (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    time.sleep(5)
                    continue
                else:
                    raise Exception("Request timeout after multiple attempts")

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    print(
                        f"Request error: {e}. Retrying... (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    time.sleep(5)
                    continue
                else:
                    raise Exception(f"Request failed after multiple attempts: {e}")

        raise Exception("Unexpected error in retry loop")

    def extract_comprehensive_data(self, contract_text: str) -> Dict[str, Any]:
        """
        Extract all contract data in one comprehensive API call with retry logic
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
        
        CONTRACT TEXT:
        {contract_text[:15000]}
        """

        try:
            response = self._ask_claude(prompt, max_tokens=1000, max_retries=3)
            return self._parse_comprehensive_response(response)

        except Exception as e:
            print(f"Comprehensive extraction failed: {e}")
            raise Exception(f"Contract analysis failed: {str(e)}")

    def _parse_comprehensive_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's structured response into database-ready format"""
        # ... (rest of your existing parsing logic remains the same)
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
            "confidence_score": Decimal("0.85"),
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
                data["contract_name"] = value[:255]
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
            import re

            numbers = re.findall(r"[\d.]+", value.replace(",", ""))
            if numbers:
                return Decimal(numbers[0])
        except:
            pass
        return None

    def _parse_date(self, value: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        try:
            import re

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
        Main method: Comprehensive contract analysis with retry logic
        """

        if not contract_text or len(contract_text.strip()) < 100:
            raise Exception("Contract text too short or empty")

        # Extract all data in one call with retries
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
