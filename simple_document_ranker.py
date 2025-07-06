#!/usr/bin/env python3
"""
Simple Document Ranker - Clean and robust document hierarchy analysis

Usage:
    python simple_document_ranker.py /path/to/SAMPLE_CONTRACTS/
"""

import os
import sys
import json
from pathlib import Path


def load_results(contracts_dir):
    """Load triage and analysis results"""
    triage_file = contracts_dir / "document_triage_results.json"
    analysis_file = contracts_dir / "selected_analysis_results.json"

    triage_data = []
    analysis_data = []

    if triage_file.exists():
        with open(triage_file, "r") as f:
            triage_data = json.load(f)

    if analysis_file.exists():
        with open(analysis_file, "r") as f:
            data = json.load(f)
            analysis_data = data.get("results", []) if isinstance(data, dict) else data

    return triage_data, analysis_data


def score_document(doc, analysis_data=None):
    """Calculate document importance score"""
    score = 0

    # Base importance
    importance_scores = {"CRITICAL": 100, "HIGH": 70, "MEDIUM": 40, "LOW": 20}
    score += importance_scores.get(doc.get("importance", "MEDIUM"), 40)

    # Document type
    type_scores = {
        "PRIMARY_CONTRACT": 50,
        "CHANGE_ORDER": 30,
        "AMENDMENT": 25,
        "LETTER_OF_INTENT": 20,
        "INSURANCE_DOCUMENT": 15,
        "SCHEDULE": 10,
    }
    score += type_scores.get(doc.get("document_type", ""), 0)

    # Status
    if doc.get("status") == "EXECUTED_SIGNED":
        score += 30
    elif doc.get("status") == "DRAFT_UNSIGNED":
        score += 10

    # Filename indicators
    filename = doc.get("filename", "").lower()
    if any(word in filename for word in ["executed", "signed", "final"]):
        score += 20

    if "revised" in filename:
        score += 10

    # Financial value (if available)
    if analysis_data:
        filename = doc.get("filename", "")
        analysis_doc = next(
            (a for a in analysis_data if a.get("filename") == filename), None
        )

        if analysis_doc and "analysis" in analysis_doc:
            contract_value = analysis_doc["analysis"].get("contract_value")
            if contract_value:
                try:
                    value = float(contract_value)
                    if value > 1000000:
                        score += 25
                    elif value > 100000:
                        score += 15
                    elif value > 10000:
                        score += 5
                except:
                    pass

    return score


def analyze_job_hierarchy(job_data, analysis_data):
    """Analyze document hierarchy for a job"""
    job_docs = job_data.get("scanned_documents", [])

    if not job_docs:
        return None

    # Score all documents
    scored_docs = []
    for doc in job_docs:
        score = score_document(doc, analysis_data)
        scored_docs.append({"document": doc, "score": score})

    # Sort by score (highest first)
    scored_docs.sort(key=lambda x: x["score"], reverse=True)

    # Identify main contract (highest scoring)
    main_contract = scored_docs[0]
    supporting_docs = scored_docs[1:]

    return {
        "job_number": job_data.get("job_number", "Unknown"),
        "job_name": job_data.get("job_name", "Unknown"),
        "main_contract": main_contract,
        "supporting_docs": supporting_docs,
        "total_docs": len(job_docs),
    }


def get_financial_summary(job_docs, analysis_data):
    """Extract financial summary"""
    total_value = 0
    contracts_with_values = []

    for doc in job_docs:
        filename = doc.get("filename", "")
        analysis_doc = next(
            (a for a in analysis_data if a.get("filename") == filename), None
        )

        if analysis_doc and "analysis" in analysis_doc:
            contract_value = analysis_doc["analysis"].get("contract_value")
            if contract_value:
                try:
                    value = float(contract_value)
                    total_value += value
                    contracts_with_values.append(
                        {
                            "filename": filename,
                            "value": value,
                            "contractor": analysis_doc["analysis"].get(
                                "contractor_name", "Unknown"
                            ),
                        }
                    )
                except:
                    pass

    return total_value, contracts_with_values


def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_document_ranker.py /path/to/SAMPLE_CONTRACTS/")
        sys.exit(1)

    contracts_directory = Path(sys.argv[1])

    if not contracts_directory.exists():
        print(f"❌ Directory not found: {contracts_directory}")
        sys.exit(1)

    print("🏆 DOCUMENT HIERARCHY ANALYZER")
    print("=" * 50)

    # Load data
    triage_data, analysis_data = load_results(contracts_directory)

    if not triage_data:
        print("❌ No triage data found")
        print("💡 Run document scanner first")
        return

    # Analyze each job
    for job_data in triage_data:
        hierarchy = analyze_job_hierarchy(job_data, analysis_data)

        if not hierarchy:
            continue

        print(f"\n🎯 JOB {hierarchy['job_number']}: {hierarchy['job_name']}")
        print("=" * 60)

        # Main contract
        main_doc = hierarchy["main_contract"]["document"]
        main_score = hierarchy["main_contract"]["score"]

        print(f"\n🏆 MAIN CONTRACT (Score: {main_score}):")
        print(f"   📄 {main_doc['filename']}")
        print(f"   📋 Type: {main_doc.get('document_type', 'Unknown')}")
        print(f"   ⭐ Importance: {main_doc.get('importance', 'Unknown')}")
        print(f"   📊 Status: {main_doc.get('status', 'Unknown')}")
        print(f"   💡 {main_doc.get('one_line_summary', 'No summary')}")

        # Supporting documents
        print(f"\n📋 SUPPORTING DOCUMENTS (Top 10):")

        for i, ranked_doc in enumerate(hierarchy["supporting_docs"][:10], 1):
            doc = ranked_doc["document"]
            score = ranked_doc["score"]

            # Determine rank emoji
            if score >= 100:
                rank_emoji = "🥇"
            elif score >= 70:
                rank_emoji = "🥈"
            elif score >= 40:
                rank_emoji = "🥉"
            else:
                rank_emoji = "📄"

            print(f"\n   {i:2d}. {rank_emoji} {doc['filename']} (Score: {score})")
            print(
                f"       📋 {doc.get('document_type', 'Unknown')} | {doc.get('importance', 'Unknown')}"
            )
            print(f"       💡 {doc.get('one_line_summary', 'No summary')}")

        # Financial summary
        if analysis_data:
            job_docs = job_data.get("scanned_documents", [])
            total_value, contracts_with_values = get_financial_summary(
                job_docs, analysis_data
            )

            if total_value > 0:
                print(f"\n💰 FINANCIAL SUMMARY:")
                print(f"   💵 Total Portfolio Value: ${total_value:,.2f}")
                print(f"   📊 Contracts Analyzed: {len(contracts_with_values)}")

                if contracts_with_values:
                    print(f"   🏆 Top Value Contracts:")
                    for contract in sorted(
                        contracts_with_values, key=lambda x: x["value"], reverse=True
                    )[:3]:
                        print(
                            f"     • ${contract['value']:,.2f} - {contract['filename']}"
                        )

    print(f"\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
