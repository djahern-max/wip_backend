# app/services/contract_intelligence_service.py
"""
Contract Intelligence Service - Based on your working single_job_scanner.py script
"""

import requests
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.config import settings


class ContractIntelligenceService:
    """
    Contract intelligence service - works exactly like your single_job_scanner.py
    """

    def __init__(self):
        if not settings.anthropic_api_key:
            raise Exception("Anthropic API key not configured")

    def classify_document(self, document_text: str, filename: str) -> Dict:
        """Classify a document - exactly like your script's quick_classify_document method"""

        text_sample = document_text[:2000]  # Use first 2K chars for speed

        prompt = f"""
        Quickly analyze this CONSTRUCTION contract document and classify it.
        
        FILENAME: {filename}
        
        DOCUMENT SAMPLE:
        {text_sample}
        
        Respond in this EXACT format:
        
        DOCUMENT_TYPE: [PRIMARY_CONTRACT, CHANGE_ORDER, LETTER_OF_INTENT, INSURANCE_DOCUMENT, SCHEDULE, AMENDMENT, PROPOSAL, INVOICE, CORRESPONDENCE, UNKNOWN]
        IMPORTANCE: [CRITICAL, HIGH, MEDIUM, LOW]
        STATUS: [EXECUTED_SIGNED, DRAFT_UNSIGNED, PROPOSAL, EXPIRED, UNKNOWN]
        KEY_PARTIES: [Main companies mentioned]
        DOLLAR_AMOUNT: [Any amounts, or NONE]
        PROJECT_INFO: [Brief project description]
        CONFIDENCE: [HIGH, MEDIUM, LOW]
        SUMMARY: [One sentence description]
        RECOMMENDATION: [ANALYZE_FULLY, REVIEW_MANUALLY, ARCHIVE, SKIP]
        """

        try:
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": settings.anthropic_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }

            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return self._parse_classification_response(
                    result["content"][0]["text"], filename
                )
            else:
                raise Exception(f"API error: {response.status_code}")

        except Exception as e:
            return {
                "filename": filename,
                "error": str(e),
                "document_type": "ERROR",
                "recommendation": "REVIEW_MANUALLY",
            }

    def _parse_classification_response(self, response: str, filename: str) -> Dict:
        """Parse Claude's response - exactly like your script's parse_response method"""

        result = {
            "filename": filename,
            "document_type": "UNKNOWN",
            "importance": "MEDIUM",
            "status": "UNKNOWN",
            "key_parties": "",
            "dollar_amount": "NONE",
            "project_info": "",
            "confidence": "MEDIUM",
            "summary": "",
            "recommendation": "REVIEW_MANUALLY",
            "classification_date": datetime.now().isoformat(),
        }

        for line in response.split("\n"):
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().upper()
            value = value.strip()

            if "DOCUMENT_TYPE" in key:
                result["document_type"] = value
            elif "IMPORTANCE" in key:
                result["importance"] = value
            elif "STATUS" in key:
                result["status"] = value
            elif "KEY_PARTIES" in key:
                result["key_parties"] = value
            elif "DOLLAR_AMOUNT" in key:
                result["dollar_amount"] = value
            elif "PROJECT_INFO" in key:
                result["project_info"] = value
            elif "CONFIDENCE" in key:
                result["confidence"] = value
            elif "SUMMARY" in key:
                result["summary"] = value
            elif "RECOMMENDATION" in key:
                result["recommendation"] = value

        return result

    def score_document_importance(self, classification: Dict) -> int:
        """Score document for ranking - enhanced logic"""

        score = 0

        # Base importance
        importance_scores = {"CRITICAL": 100, "HIGH": 70, "MEDIUM": 40, "LOW": 20}
        score += importance_scores.get(classification.get("importance", "MEDIUM"), 40)

        # Document type
        type_scores = {
            "PRIMARY_CONTRACT": 50,
            "CHANGE_ORDER": 30,
            "AMENDMENT": 25,
            "INSURANCE_DOCUMENT": 15,
            "CORRESPONDENCE": 10,
        }
        score += type_scores.get(classification.get("document_type", ""), 0)

        # Status bonus
        if classification.get("status") == "EXECUTED_SIGNED":
            score += 30
        elif classification.get("status") == "DRAFT_UNSIGNED":
            score += 10

        # Enhanced filename analysis
        filename = classification.get("filename", "").lower()

        # Strong indicators of main/final contract
        if any(word in filename for word in ["executed", "signed", "final"]):
            score += 25

        # Clean/final version indicators
        if "clean" in filename:
            score += 20

        # Version progression
        if "r1" in filename or "rev1" in filename:
            score += 15
        elif "r2" in filename or "rev2" in filename:
            score += 18
        elif "r3" in filename or "rev3" in filename:
            score += 22

        # Draft/markup indicators (lower priority)
        if any(word in filename for word in ["markup", "mark up", "draft"]):
            score -= 10

        # File size bonus
        text_length = classification.get("text_length", 0)
        if text_length > 100000:  # >100k chars
            score += 15
        elif text_length > 50000:  # >50k chars
            score += 10
        elif text_length > 20000:  # >20k chars
            score += 5

        return score

    def identify_main_contract(
        self, contract_classifications: List[Dict]
    ) -> Optional[Dict]:
        """Identify main contract from classifications"""

        if not contract_classifications:
            return None

        # Score all documents
        scored_docs = []
        for classification in contract_classifications:
            score = self.score_document_importance(classification)
            scored_docs.append({"classification": classification, "score": score})

        # Sort by score (highest first)
        scored_docs.sort(key=lambda x: x["score"], reverse=True)

        # Look for clear indicators of the main contract
        main_contract = None
        primary_contracts = [
            doc
            for doc in scored_docs
            if doc["classification"].get("document_type") == "PRIMARY_CONTRACT"
        ]

        if primary_contracts:
            # Among primary contracts, look for the most definitive one
            for doc in primary_contracts:
                filename = doc["classification"].get("filename", "").lower()

                if any(
                    indicator in filename
                    for indicator in ["executed", "clean", "final", "r1", "signed"]
                ):
                    main_contract = doc
                    break

            # If no clear main contract found, use highest scoring primary contract
            if not main_contract:
                main_contract = primary_contracts[0]
        else:
            # No primary contracts found, use highest scoring document
            main_contract = scored_docs[0]

        # Add ranking metadata
        main_contract["classification"]["is_main_contract"] = True
        main_contract["classification"]["importance_score"] = main_contract["score"]
        main_contract["classification"]["total_documents"] = len(
            contract_classifications
        )
        main_contract["classification"]["ranking_reason"] = self._get_ranking_reason(
            main_contract["classification"], primary_contracts
        )

        return main_contract["classification"]

    def _get_ranking_reason(
        self, main_contract: Dict, all_primary_contracts: List[Dict]
    ) -> str:
        """Explain why this contract was chosen as main"""
        filename = main_contract.get("filename", "").lower()

        if "executed" in filename:
            return "Identified as executed/signed contract"
        elif "clean" in filename:
            return "Identified as clean/final version"
        elif "final" in filename:
            return "Identified as final version"
        elif "r1" in filename or "signed" in filename:
            return "Identified as revised/signed version"
        elif len(all_primary_contracts) > 1:
            return (
                f"Highest scoring among {len(all_primary_contracts)} primary contracts"
            )
        else:
            return "Only primary contract found"

    def get_ranked_document_list(
        self, contract_classifications: List[Dict]
    ) -> List[Dict]:
        """Get all documents ranked by importance"""

        if not contract_classifications:
            return []

        # First identify the main contract
        main_contract_data = self.identify_main_contract(contract_classifications)
        main_filename = (
            main_contract_data.get("filename") if main_contract_data else None
        )

        # Score all documents
        scored_docs = []
        for classification in contract_classifications:
            score = self.score_document_importance(classification)

            # Add score and ranking info to classification
            enhanced_classification = classification.copy()
            enhanced_classification["importance_score"] = score

            # Set main contract flag
            if main_filename and classification.get("filename") == main_filename:
                enhanced_classification["is_main_contract"] = True
                enhanced_classification["ranking_reason"] = main_contract_data.get(
                    "ranking_reason"
                )
            else:
                enhanced_classification["is_main_contract"] = False

            scored_docs.append(enhanced_classification)

        # Sort by score (highest first)
        scored_docs.sort(key=lambda x: x["importance_score"], reverse=True)

        # Add rank numbers
        for i, doc in enumerate(scored_docs, 1):
            doc["rank"] = i

            # Determine document priority level
            if doc.get("is_main_contract"):
                doc["priority_level"] = "MAIN_CONTRACT"
            elif doc.get("document_type") == "PRIMARY_CONTRACT" and i <= 3:
                doc["priority_level"] = "HIGH_PRIORITY"
            elif doc.get("recommendation") == "ANALYZE_FULLY":
                doc["priority_level"] = "ANALYZE_RECOMMENDED"
            else:
                doc["priority_level"] = "SUPPORTING_DOCUMENT"

        return scored_docs
