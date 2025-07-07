# app/services/contract_intelligence_service.py
"""
Integrated Contract Intelligence Service
Combines document classification, ranking, and hierarchy analysis
"""

import json
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.claude_contract_analyzer import ComprehensiveClaudeAnalyzer
from app.models.contract import Contract
from app.models.contract_analysis import ContractAnalysis


class ContractIntelligenceService:
    """
    Unified service for contract document intelligence
    Handles classification, ranking, and main contract identification
    """

    def __init__(self):
        self.analyzer = ComprehensiveClaudeAnalyzer()

    def classify_document(self, document_text: str, filename: str) -> Dict:
        """Fast document classification using Claude"""

        text_sample = document_text[:2000]  # Use first 2K chars for speed

        prompt = f"""
        Quickly analyze this CONSTRUCTION contract document and classify it.
        
        FILENAME: {filename}
        
        DOCUMENT SAMPLE:
        {text_sample}
        
        Respond in this EXACT format:
        
        DOCUMENT_TYPE: [PRIMARY_CONTRACT, CHANGE_ORDER, AMENDMENT, INSURANCE_DOCUMENT, CORRESPONDENCE, UNKNOWN]
        IMPORTANCE: [CRITICAL, HIGH, MEDIUM, LOW]
        STATUS: [EXECUTED_SIGNED, DRAFT_UNSIGNED, PROPOSAL, EXPIRED, UNKNOWN]
        MAIN_PARTIES: [Primary companies mentioned]
        CONTRACT_VALUE: [Any dollar amounts, or NONE]
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
                "importance": "UNKNOWN",
                "recommendation": "REVIEW_MANUALLY",
            }

    def _parse_classification_response(self, response: str, filename: str) -> Dict:
        """Parse Claude's structured response"""

        result = {
            "filename": filename,
            "document_type": "UNKNOWN",
            "importance": "MEDIUM",
            "status": "UNKNOWN",
            "main_parties": [],
            "contract_value": "NONE",
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
            elif "MAIN_PARTIES" in key:
                result["main_parties"] = [p.strip() for p in value.split(",")]
            elif "CONTRACT_VALUE" in key:
                result["contract_value"] = value
            elif "PROJECT_INFO" in key:
                result["project_info"] = value
            elif "CONFIDENCE" in key:
                result["confidence"] = value
            elif "SUMMARY" in key:
                result["summary"] = value
            elif "RECOMMENDATION" in key:
                result["recommendation"] = value

        return result

    def score_document_importance(
        self, classification: Dict, analysis_data: Optional[Dict] = None
    ) -> int:
        """Calculate document importance score for ranking"""

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

        # Filename indicators
        filename = classification.get("filename", "").lower()
        if any(word in filename for word in ["executed", "signed", "final"]):
            score += 20

        if "revised" in filename:
            score += 10

        # Financial value (if available from analysis)
        if analysis_data and "contract_value" in analysis_data:
            try:
                value = float(analysis_data["contract_value"])
                if value > 1000000:
                    score += 25
                elif value > 100000:
                    score += 15
                elif value > 10000:
                    score += 5
            except:
                pass

        return score

    def identify_main_contract(
        self, contract_classifications: List[Dict]
    ) -> Optional[Dict]:
        """Identify the main contract from a collection of documents"""

        if not contract_classifications:
            return None

        # Score all documents
        scored_docs = []
        for classification in contract_classifications:
            score = self.score_document_importance(classification)
            scored_docs.append({"classification": classification, "score": score})

        # Sort by score (highest first)
        scored_docs.sort(key=lambda x: x["score"], reverse=True)

        # Return the highest scoring document as main contract
        main_contract = scored_docs[0]

        # Add ranking metadata
        main_contract["classification"]["is_main_contract"] = True
        main_contract["classification"]["importance_score"] = main_contract["score"]
        main_contract["classification"]["total_documents"] = len(
            contract_classifications
        )

        return main_contract["classification"]

    def analyze_contract_portfolio(self, file_paths: List[Path]) -> Dict:
        """
        Analyze a collection of contract documents
        Returns classification and hierarchy analysis
        """

        results = {
            "total_documents": len(file_paths),
            "classifications": [],
            "main_contract": None,
            "supporting_documents": [],
            "analysis_date": datetime.now().isoformat(),
            "errors": [],
        }

        # Classify all documents
        for file_path in file_paths:
            try:
                # Extract text
                document_text = extract_text_from_pdf(str(file_path))

                if not document_text or len(document_text.strip()) < 50:
                    raise Exception("Insufficient text extracted")

                # Classify
                classification = self.classify_document(document_text, file_path.name)
                classification["file_path"] = str(file_path)
                classification["text_length"] = len(document_text)

                results["classifications"].append(classification)

            except Exception as e:
                error_doc = {
                    "filename": file_path.name,
                    "file_path": str(file_path),
                    "error": str(e),
                    "document_type": "ERROR",
                }
                results["errors"].append(error_doc)

        # Identify main contract and supporting documents
        if results["classifications"]:
            main_contract = self.identify_main_contract(results["classifications"])

            if main_contract:
                results["main_contract"] = main_contract

                # Remaining documents are supporting
                results["supporting_documents"] = [
                    doc
                    for doc in results["classifications"]
                    if doc["filename"] != main_contract["filename"]
                ]

                # Sort supporting docs by importance score
                for doc in results["supporting_documents"]:
                    doc["importance_score"] = self.score_document_importance(doc)

                results["supporting_documents"].sort(
                    key=lambda x: x["importance_score"], reverse=True
                )

        return results

    def get_analysis_recommendations(self, portfolio_analysis: Dict) -> Dict:
        """Generate actionable recommendations from portfolio analysis"""

        recommendations = {
            "immediate_actions": [],
            "full_analysis_candidates": [],
            "manual_review_needed": [],
            "estimated_cost": 0,
            "estimated_time_minutes": 0,
        }

        # Main contract should always be analyzed if not done already
        if portfolio_analysis.get("main_contract"):
            main_contract = portfolio_analysis["main_contract"]
            if main_contract.get("recommendation") in [
                "ANALYZE_FULLY",
                "REVIEW_MANUALLY",
            ]:
                recommendations["immediate_actions"].append(
                    {
                        "action": "analyze_main_contract",
                        "filename": main_contract["filename"],
                        "reason": "Primary contract document identified",
                        "priority": "CRITICAL",
                    }
                )
                recommendations["full_analysis_candidates"].append(main_contract)

        # Add other high-value documents
        for doc in portfolio_analysis.get("supporting_documents", []):
            if doc.get("recommendation") == "ANALYZE_FULLY":
                recommendations["full_analysis_candidates"].append(doc)
            elif doc.get("recommendation") == "REVIEW_MANUALLY":
                recommendations["manual_review_needed"].append(doc)

        # Calculate estimates
        full_analysis_count = len(recommendations["full_analysis_candidates"])
        recommendations["estimated_cost"] = (
            full_analysis_count * 0.10
        )  # $0.10 per document
        recommendations["estimated_time_minutes"] = (
            full_analysis_count * 2
        )  # 2 minutes per document

        return recommendations


# Integration with existing API
class ContractIntelligenceAPI:
    """API integration for contract intelligence"""

    def __init__(self):
        self.intelligence_service = ContractIntelligenceService()

    def analyze_uploaded_contracts(self, db: Session, contract_ids: List[int]) -> Dict:
        """Analyze multiple uploaded contracts and identify main contract"""

        contracts = db.query(Contract).filter(Contract.id.in_(contract_ids)).all()

        if not contracts:
            raise Exception("No contracts found")

        # Classify all documents
        classifications = []

        for contract in contracts:
            try:
                # Get decrypted text
                raw_text = contract.raw_text

                if not raw_text:
                    continue

                # Classify
                classification = self.intelligence_service.classify_document(
                    raw_text, contract.filename
                )
                classification["contract_id"] = contract.id
                classification["text_length"] = len(raw_text)

                classifications.append(classification)

            except Exception as e:
                print(f"Classification failed for contract {contract.id}: {e}")
                continue

        # Identify main contract
        main_contract = self.intelligence_service.identify_main_contract(
            classifications
        )

        # Generate recommendations
        portfolio_analysis = {
            "classifications": classifications,
            "main_contract": main_contract,
            "supporting_documents": (
                [
                    doc
                    for doc in classifications
                    if doc.get("contract_id") != main_contract.get("contract_id")
                ]
                if main_contract
                else classifications
            ),
        }

        recommendations = self.intelligence_service.get_analysis_recommendations(
            portfolio_analysis
        )

        return {
            "main_contract": main_contract,
            "supporting_documents": portfolio_analysis["supporting_documents"],
            "recommendations": recommendations,
            "total_contracts": len(contracts),
            "classified_contracts": len(classifications),
            "analysis_date": datetime.now().isoformat(),
        }
