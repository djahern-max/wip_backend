import requests
from typing import Optional
from app.core.config import settings


class AIContractAnalyzer:
    def __init__(self):
        pass

    def ask_question(self, contract_text: str, question: str) -> str:
        """Ask OpenAI a direct question about the contract - NO JSON, NO STRUCTURE"""

        if not settings.openai_api_key:
            raise Exception("OpenAI API key not configured")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        # Direct, simple prompt
        prompt = f"""
        Read this contract and answer the question directly. If you cannot find the answer, say "Information not found in contract."
        
        QUESTION: {question}
        
        CONTRACT TEXT:
        {contract_text}
        
        Give a direct answer. Do not explain your reasoning.
        """

        data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 200,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code}")

            result = response.json()
            return result["choices"][0]["message"]["content"].strip()

        except Exception as e:
            raise Exception(f"OpenAI failed: {str(e)}")

    def get_contract_value(self, contract_text: str) -> str:
        """Specific method to get contract value"""
        return self.ask_question(contract_text, "What is the total contract value?")

    def get_contract_number(self, contract_text: str) -> str:
        """Specific method to get contract number"""
        return self.ask_question(
            contract_text, "What is the contract number or identifier?"
        )

    def get_parties(self, contract_text: str) -> str:
        """Specific method to get contracting parties"""
        return self.ask_question(contract_text, "Who are the contracting parties?")
