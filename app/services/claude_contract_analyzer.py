import requests
import re
from typing import Optional, Dict
from decimal import Decimal
from app.core.config import settings


class ClaudeContractAnalyzer:
    """
    Production-ready Claude contract analyzer
    Fast, accurate, no fallbacks - Claude only
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

    def _ask_claude(self, prompt: str, max_tokens: int = 300) -> str:
        """Send prompt to Claude and return response"""

        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(
            self.base_url, headers=self.headers, json=data, timeout=30
        )

        if response.status_code != 200:
            raise Exception(
                f"Claude API error: {response.status_code} - {response.text}"
            )

        result = response.json()
        return result["content"][0]["text"].strip()

    def extract_contract_value(self, contract_text: str) -> Optional[Decimal]:
        """Extract contract value as a Decimal for database storage"""

        prompt = f"""
        Extract the total contract value or subcontract value from this contract.
        Return ONLY the numeric amount without dollar signs or commas.
        If no value is found, return "NOT_FOUND".
        
        Examples:
        - "One Million, Five Hundred Thousand" → 1500000
        - "$1,582,389.00" → 1582389
        - "No value found" → NOT_FOUND
        
        CONTRACT TEXT:
        {contract_text}
        """

        try:
            response = self._ask_claude(prompt, max_tokens=100)

            if "NOT_FOUND" in response.upper():
                return None

            # Extract numbers from response
            numbers = re.findall(r"[\d.]+", response)
            if numbers:
                return Decimal(numbers[0])

            return None

        except Exception as e:
            print(f"Contract value extraction failed: {e}")
            return None

    def extract_contract_number(self, contract_text: str) -> Optional[str]:
        """Extract contract/project number"""

        prompt = f"""
        Extract the main contract number, project number, or identifier from this contract.
        Look for patterns like:
        - CTDOT numbers (e.g., "CTDOT # 172-517")
        - Project numbers
        - Contract IDs
        
        Return ONLY the identifier. If no number is found, return "NOT_FOUND".
        
        CONTRACT TEXT:
        {contract_text}
        """

        try:
            response = self._ask_claude(prompt, max_tokens=100)

            if "NOT_FOUND" in response.upper():
                return None

            # Clean up the response - remove common prefixes
            clean_response = (
                response.replace("CTDOT #", "").replace("CTDOT", "").strip()
            )
            clean_response = re.sub(
                r"^[#\s]+", "", clean_response
            )  # Remove leading # and spaces

            return clean_response if clean_response else None

        except Exception as e:
            print(f"Contract number extraction failed: {e}")
            return None

    def extract_contract_name(self, contract_text: str) -> Optional[str]:
        """Extract project name or contract title"""

        prompt = f"""
        Extract the project name, work description, or contract title from this contract.
        Look for the main work being performed (e.g., "Metallizing of 19 Bridges Along I-395 Corridor").
        
        Return a concise project name. If no clear project name is found, return "NOT_FOUND".
        
        CONTRACT TEXT:
        {contract_text}
        """

        try:
            response = self._ask_claude(prompt, max_tokens=150)

            if "NOT_FOUND" in response.upper():
                return None

            # Clean up the response
            clean_response = response.strip('"').strip("'").strip()
            return clean_response if clean_response else None

        except Exception as e:
            print(f"Contract name extraction failed: {e}")
            return None

    def extract_all_data(self, contract_text: str) -> Dict[str, Optional[str]]:
        """Extract all key contract data in one comprehensive call"""

        prompt = f"""
        Extract the following information from this contract:
        
        1. Contract/Project Number (CTDOT numbers, project IDs, etc.)
        2. Total Contract Value (dollar amount as number only)
        3. Project Name/Description (main work being performed)
        
        Format your response EXACTLY like this:
        CONTRACT_NUMBER: [value or NOT_FOUND]
        CONTRACT_VALUE: [numeric value only or NOT_FOUND]
        PROJECT_NAME: [project description or NOT_FOUND]
        
        Examples:
        CONTRACT_NUMBER: 172-517
        CONTRACT_VALUE: 1582389
        PROJECT_NAME: Metallizing of 19 Bridges Along I-395 Corridor
        
        CONTRACT TEXT:
        {contract_text}
        """

        try:
            response = self._ask_claude(prompt, max_tokens=300)

            # Parse the structured response
            data = {
                "contract_number": None,
                "contract_value": None,
                "contract_name": None,
            }

            for line in response.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    value = value.strip()

                    if "CONTRACT_NUMBER" in key.upper() and value != "NOT_FOUND":
                        # Clean contract number
                        clean_value = (
                            value.replace("CTDOT #", "").replace("CTDOT", "").strip()
                        )
                        clean_value = re.sub(r"^[#\s]+", "", clean_value)
                        data["contract_number"] = clean_value if clean_value else None

                    elif "CONTRACT_VALUE" in key.upper() and value != "NOT_FOUND":
                        # Extract numeric value
                        numbers = re.findall(r"[\d.]+", value)
                        if numbers:
                            try:
                                data["contract_value"] = Decimal(numbers[0])
                            except:
                                data["contract_value"] = None

                    elif "PROJECT_NAME" in key.upper() and value != "NOT_FOUND":
                        data["contract_name"] = value.strip('"').strip("'").strip()

            return data

        except Exception as e:
            print(f"Comprehensive extraction failed: {e}")
            # Fallback to individual extractions
            return {
                "contract_number": self.extract_contract_number(contract_text),
                "contract_value": self.extract_contract_value(contract_text),
                "contract_name": self.extract_contract_name(contract_text),
            }

    def analyze_contract(self, contract_text: str) -> Dict[str, any]:
        """
        Main method: Analyze contract and return all extracted data
        Returns data ready for database storage
        """

        if not contract_text or len(contract_text.strip()) < 100:
            raise Exception("Contract text too short or empty")

        # Extract all data
        extracted_data = self.extract_all_data(contract_text)

        return {
            "success": True,
            "contract_number": extracted_data.get("contract_number"),
            "contract_value": extracted_data.get("contract_value"),
            "contract_name": extracted_data.get("contract_name"),
            "analysis_provider": "claude-3-sonnet",
            "text_length": len(contract_text),
        }
