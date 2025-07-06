import requests
import json
from typing import Optional, Dict, Any
from app.core.config import settings


class AIContractAnalyzer:
    """
    AI-powered contract analyzer using Claude API (Anthropic)
    Fallback support for other providers if needed
    """

    def __init__(self):
        self.claude_api_key = getattr(settings, "anthropic_api_key", None)
        self.openai_api_key = getattr(settings, "openai_api_key", None)
        self.runpod_endpoint = getattr(settings, "runpod_endpoint", None)
        self.runpod_api_key = getattr(settings, "runpod_api_key", None)

    def ask_question_claude(self, contract_text: str, question: str) -> str:
        """Ask Claude a direct question about the contract"""

        if not self.claude_api_key:
            raise Exception("Anthropic API key not configured")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.claude_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Direct, focused prompt for contract analysis
        prompt = f"""
        Analyze this contract and answer the question directly and concisely. 
        If you cannot find the answer, respond with "Information not found in contract."
        
        QUESTION: {question}
        
        CONTRACT TEXT:
        {contract_text}
        
        Provide only the direct answer without explanation.
        """

        data = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code != 200:
                raise Exception(
                    f"Claude API error: {response.status_code} - {response.text}"
                )

            result = response.json()
            return result["content"][0]["text"].strip()

        except Exception as e:
            raise Exception(f"Claude API failed: {str(e)}")

    def ask_question_openai(self, contract_text: str, question: str) -> str:
        """Fallback: Ask OpenAI a question (with rate limiting awareness)"""

        if not self.openai_api_key:
            raise Exception("OpenAI API key not configured")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        prompt = f"""
        Read this contract and answer the question directly. If you cannot find the answer, say "Information not found in contract."
        
        QUESTION: {question}
        
        CONTRACT TEXT:
        {contract_text}
        
        Give a direct answer without explanation.
        """

        data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 200,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 429:
                raise Exception("OpenAI rate limit exceeded")
            elif response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code}")

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            raise Exception(f"OpenAI failed: {str(e)}")

    def ask_question_runpod(self, contract_text: str, question: str) -> str:
        """Use Runpod endpoint for contract analysis"""

        if not self.runpod_endpoint or not self.runpod_api_key:
            raise Exception("Runpod endpoint or API key not configured")

        headers = {
            "Authorization": f"Bearer {self.runpod_api_key}",
            "Content-Type": "application/json",
        }

        # Adjust this payload based on your Runpod setup
        data = {
            "input": {
                "prompt": f"Question: {question}\n\nContract: {contract_text}\n\nAnswer:",
                "max_tokens": 200,
                "temperature": 0,
            }
        }

        try:
            response = requests.post(
                self.runpod_endpoint, headers=headers, json=data, timeout=60
            )

            if response.status_code != 200:
                raise Exception(f"Runpod API error: {response.status_code}")

            result = response.json()
            # Adjust based on your Runpod response structure
            return result.get("output", "").strip()

        except Exception as e:
            raise Exception(f"Runpod failed: {str(e)}")

    def ask_question(self, contract_text: str, question: str) -> str:
        """
        Ask a question about the contract with automatic fallback between providers
        Priority: Claude -> Runpod -> OpenAI
        """

        # Try Claude first (recommended)
        if self.claude_api_key:
            try:
                return self.ask_question_claude(contract_text, question)
            except Exception as e:
                print(f"Claude failed, trying fallback: {e}")

        # Try Runpod second
        if self.runpod_endpoint and self.runpod_api_key:
            try:
                return self.ask_question_runpod(contract_text, question)
            except Exception as e:
                print(f"Runpod failed, trying OpenAI: {e}")

        # Try OpenAI last (rate limiting issues)
        if self.openai_api_key:
            try:
                return self.ask_question_openai(contract_text, question)
            except Exception as e:
                print(f"OpenAI failed: {e}")

        raise Exception("All AI providers failed or not configured")

    def get_contract_value(self, contract_text: str) -> str:
        """Extract contract value from text"""
        return self.ask_question(
            contract_text,
            "What is the total contract value or subcontract value in dollars? Include the exact amount.",
        )

    def get_contract_number(self, contract_text: str) -> str:
        """Extract contract number/identifier"""
        return self.ask_question(
            contract_text,
            "What is the contract number, project number, or main identifier? Look for CTDOT numbers, project IDs, etc.",
        )

    def get_contract_name(self, contract_text: str) -> str:
        """Extract contract or project name"""
        return self.ask_question(
            contract_text,
            "What is the project name or contract title? Look for the main work description.",
        )

    def get_contracting_parties(self, contract_text: str) -> str:
        """Extract the main contracting parties"""
        return self.ask_question(
            contract_text,
            "Who are the main contracting parties? List the contractor and subcontractor company names.",
        )

    def get_contract_dates(self, contract_text: str) -> str:
        """Extract important contract dates"""
        return self.ask_question(
            contract_text,
            "What are the key dates in this contract? Include agreement date, start date, end date if mentioned.",
        )

    def extract_all_key_data(self, contract_text: str) -> Dict[str, str]:
        """Extract all key contract information in one call"""

        comprehensive_question = """
        Extract the following key information from this contract:
        1. Contract/Project Number
        2. Contract Value (dollar amount)
        3. Project Name/Title
        4. Contractor Company Name
        5. Subcontractor Company Name
        6. Agreement Date
        
        Format your response as:
        Contract Number: [answer]
        Contract Value: [answer]
        Project Name: [answer]
        Contractor: [answer]
        Subcontractor: [answer]
        Agreement Date: [answer]
        """

        try:
            response = self.ask_question(contract_text, comprehensive_question)

            # Parse the structured response
            data = {}
            for line in response.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip().lower().replace(" ", "_")] = value.strip()

            return data

        except Exception as e:
            # Fallback to individual questions
            return {
                "contract_number": self.get_contract_number(contract_text),
                "contract_value": self.get_contract_value(contract_text),
                "project_name": self.get_contract_name(contract_text),
                "contracting_parties": self.get_contracting_parties(contract_text),
            }
