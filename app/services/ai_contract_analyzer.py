import requests
import json
import re
from typing import Dict, Optional
from app.core.config import settings


class AIContractAnalyzer:
    def __init__(self):
        pass
    
    def analyze_contract(self, contract_text: str) -> Dict[str, Optional[str]]:
        """Use AI to analyze contract and extract key information"""
        
        if not settings.openai_api_key:
            raise Exception("OpenAI API key not configured")
        
        # Extract key sections that likely contain contract value
        text_to_analyze = self._extract_key_sections(contract_text)
        
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
        Extract contract information from this text and return as JSON:
        {{
          "contract_number": "contract or project number",
          "contract_name": "project name", 
          "contract_value": 123456.78
        }}
        
        Look for contract values in formats like:
        - $1,234,567.89
        - One Million Five Hundred Thousand Dollars ($1,500,000.00)
        - Total: $xxx,xxx.xx
        - Contract Amount: $xxx,xxx.xx
        
        Text to analyze:
        {text_to_analyze[:3000]}
        """
        
        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 300
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"].strip()
            
            # Parse the JSON response
            extracted_data = json.loads(ai_response)
            return extracted_data
            
        except requests.RequestException as e:
            raise Exception(f"Network error calling OpenAI: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"AI returned invalid JSON: {ai_response}")
        except KeyError as e:
            raise Exception(f"Unexpected OpenAI response format: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenAI analysis failed: {str(e)}")
    
    def _extract_key_sections(self, text: str) -> str:
        """Extract sections most likely to contain contract values"""
        
        # Start with the beginning of the contract
        result = text[:1000]
        
        # Look for sections that might contain financial info
        financial_keywords = [
            'amount', 'value', 'total', 'sum', 'dollars', 'price', 
            'compensation', 'payment', 'cost', '$', 'million', 'thousand'
        ]
        
        lines = text.split('\n')
        financial_lines = []
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in financial_keywords):
                # Include context around financial lines
                start = max(0, i-2)
                end = min(len(lines), i+3)
                financial_lines.extend(lines[start:end])
        
        # Add financial sections to the result
        if financial_lines:
            result += "\n\nFINANCIAL SECTIONS:\n" + "\n".join(financial_lines[:50])
        
        return result
