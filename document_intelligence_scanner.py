#!/usr/bin/env python3
"""
Document Intelligence Scanner
Quick triage system to identify document types and importance before full analysis

Usage:
    python document_intelligence_scanner.py /path/to/SAMPLE_CONTRACTS/

Features:
- Fast document classification (15-30 seconds per document)
- Identifies document type, importance, and key details
- Creates prioritized action plan
- Minimal cost (~$0.01-0.03 per document)
- Helps decide which documents deserve full analysis
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.pdf_extractor import extract_text_from_pdf
from app.core.config import settings


class DocumentIntelligenceScanner:
    """
    Quick document classifier and triage system
    """

    def __init__(self, contracts_directory: str):
        self.contracts_dir = Path(contracts_directory)
        self.results = []
        self.scan_cache = {}

        # Load previous scan results
        self.cache_file = self.contracts_dir / "document_scan_cache.json"
        self.load_scan_cache()

        # Verify Claude API
        if not settings.anthropic_api_key:
            raise Exception("ANTHROPIC_API_KEY not configured")

    def load_scan_cache(self):
        """Load previous scan results to avoid rescanning"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.scan_cache = json.load(f)
                print(f"📂 Loaded {len(self.scan_cache)} cached scans")
            except Exception as e:
                print(f"⚠️ Could not load scan cache: {e}")

    def save_scan_cache(self):
        """Save scan results for future use"""
        with open(self.cache_file, "w") as f:
            json.dump(self.scan_cache, f, indent=2, default=str)

    def quick_classify_document(self, document_text: str, filename: str) -> Dict:
        """
        Fast document classification using Claude
        Returns document type, importance, and key details
        """

        # Use only first 2000 characters for quick scan
        text_sample = document_text[:2000]

        prompt = f"""
        Quickly analyze this document and classify it. This is a CONSTRUCTION/INFRASTRUCTURE contract document.
        
        DOCUMENT FILENAME: {filename}
        
        DOCUMENT TEXT SAMPLE:
        {text_sample}
        
        Provide analysis in this EXACT format:
        
        DOCUMENT_TYPE: [Choose ONE: PRIMARY_CONTRACT, CHANGE_ORDER, LETTER_OF_INTENT, INSURANCE_DOCUMENT, SCHEDULE, AMENDMENT, PROPOSAL, INVOICE, CORRESPONDENCE, UNKNOWN]
        
        IMPORTANCE: [Choose ONE: CRITICAL, HIGH, MEDIUM, LOW]
        
        STATUS: [Choose ONE: EXECUTED_SIGNED, DRAFT_UNSIGNED, PROPOSAL, EXPIRED, UNKNOWN]
        
        KEY_PARTIES: [List main companies/parties mentioned]
        
        DOLLAR_AMOUNT: [Any dollar amounts mentioned, or NONE]
        
        PROJECT_REFERENCE: [Project name/number if mentioned, or NONE]
        
        EXECUTION_DATE: [Date if this appears to be signed/executed, or NONE]
        
        CONFIDENCE: [HIGH, MEDIUM, LOW - how confident are you in this classification]
        
        ONE_LINE_SUMMARY: [What this document is in plain English]
        
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
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                claude_response = result["content"][0]["text"].strip()
                return self.parse_classification_response(claude_response, filename)
            else:
                raise Exception(f"Claude API error: {response.status_code}")

        except Exception as e:
            return {
                "document_type": "UNKNOWN",
                "importance": "MEDIUM",
                "status": "UNKNOWN",
                "key_parties": [],
                "dollar_amount": "NONE",
                "project_reference": "NONE",
                "execution_date": "NONE",
                "confidence": "LOW",
                "one_line_summary": f"Classification failed: {str(e)}",
                "recommendation": "REVIEW_MANUALLY",
                "error": str(e),
            }

    def parse_classification_response(self, response: str, filename: str) -> Dict:
        """Parse Claude's structured response"""

        classification = {
            "document_type": "UNKNOWN",
            "importance": "MEDIUM",
            "status": "UNKNOWN",
            "key_parties": [],
            "dollar_amount": "NONE",
            "project_reference": "NONE",
            "execution_date": "NONE",
            "confidence": "MEDIUM",
            "one_line_summary": "Document classification",
            "recommendation": "REVIEW_MANUALLY",
        }

        # Parse each line of the response
        for line in response.split("\n"):
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().upper()
            value = value.strip()

            if "DOCUMENT_TYPE" in key:
                classification["document_type"] = value
            elif "IMPORTANCE" in key:
                classification["importance"] = value
            elif "STATUS" in key:
                classification["status"] = value
            elif "KEY_PARTIES" in key:
                classification["key_parties"] = [
                    p.strip() for p in value.split(",") if p.strip()
                ]
            elif "DOLLAR_AMOUNT" in key:
                classification["dollar_amount"] = value
            elif "PROJECT_REFERENCE" in key:
                classification["project_reference"] = value
            elif "EXECUTION_DATE" in key:
                classification["execution_date"] = value
            elif "CONFIDENCE" in key:
                classification["confidence"] = value
            elif "ONE_LINE_SUMMARY" in key:
                classification["one_line_summary"] = value
            elif "RECOMMENDATION" in key:
                classification["recommendation"] = value

        return classification

    def scan_document(self, file_path: Path) -> Dict:
        """Scan a single document"""

        file_key = str(file_path)

        # Check cache first
        if file_key in self.scan_cache:
            cached_result = self.scan_cache[file_key]
            cached_result["from_cache"] = True
            return cached_result

        try:
            # Extract text
            document_text = extract_text_from_pdf(str(file_path))

            if not document_text or len(document_text.strip()) < 50:
                raise Exception("Insufficient text extracted")

            # Quick classify
            classification = self.quick_classify_document(document_text, file_path.name)

            # Add metadata
            scan_result = {
                "filename": file_path.name,
                "file_path": str(file_path),
                "file_size_kb": file_path.stat().st_size // 1024,
                "text_length": len(document_text),
                "scan_date": datetime.now().isoformat(),
                "from_cache": False,
                **classification,
            }

            # Cache the result
            self.scan_cache[file_key] = scan_result

            return scan_result

        except Exception as e:
            error_result = {
                "filename": file_path.name,
                "file_path": str(file_path),
                "error": str(e),
                "scan_date": datetime.now().isoformat(),
                "document_type": "ERROR",
                "importance": "UNKNOWN",
                "recommendation": "REVIEW_MANUALLY",
                "one_line_summary": f"Scan failed: {str(e)}",
            }

            return error_result

    def scan_job_directory(self, job_dir: Path) -> Dict:
        """Scan all documents in a job directory"""

        job_number = job_dir.name[:4]
        job_name = job_dir.name

        print(f"\n🔍 Scanning Job {job_number}: {job_name}")
        print("=" * 60)

        pdf_files = list(job_dir.glob("*.pdf"))
        scanned_docs = []

        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"📄 Scanning ({i}/{len(pdf_files)}): {pdf_file.name}")

            scan_result = self.scan_document(pdf_file)
            scanned_docs.append(scan_result)

            # Show quick summary
            if "error" not in scan_result:
                print(f"   📋 Type: {scan_result['document_type']}")
                print(f"   ⭐ Importance: {scan_result['importance']}")
                print(f"   💡 {scan_result['one_line_summary']}")
                print(f"   🎯 Recommendation: {scan_result['recommendation']}")
            else:
                print(f"   ❌ Error: {scan_result['error']}")

            # Small delay to be respectful
            if not scan_result.get("from_cache", False):
                time.sleep(0.5)

        # Analyze job-level patterns
        critical_docs = [d for d in scanned_docs if d.get("importance") == "CRITICAL"]
        executed_contracts = [
            d for d in scanned_docs if d.get("status") == "EXECUTED_SIGNED"
        ]
        primary_contracts = [
            d for d in scanned_docs if d.get("document_type") == "PRIMARY_CONTRACT"
        ]

        job_summary = {
            "job_number": job_number,
            "job_name": job_name,
            "job_directory": str(job_dir),
            "total_documents": len(pdf_files),
            "scanned_documents": scanned_docs,
            "critical_documents": len(critical_docs),
            "executed_contracts": len(executed_contracts),
            "primary_contracts": len(primary_contracts),
            "scan_date": datetime.now().isoformat(),
        }

        return job_summary

    def generate_triage_report(self, all_job_results: List[Dict]) -> str:
        """Generate actionable triage report"""

        # Collect all documents across jobs
        all_docs = []
        for job in all_job_results:
            for doc in job["scanned_documents"]:
                doc["job_number"] = job["job_number"]
                doc["job_name"] = job["job_name"]
                all_docs.append(doc)

        # Categorize documents
        critical_docs = [d for d in all_docs if d.get("importance") == "CRITICAL"]
        analyze_fully = [
            d for d in all_docs if d.get("recommendation") == "ANALYZE_FULLY"
        ]
        executed_contracts = [
            d for d in all_docs if d.get("status") == "EXECUTED_SIGNED"
        ]
        primary_contracts = [
            d for d in all_docs if d.get("document_type") == "PRIMARY_CONTRACT"
        ]

        # Document type breakdown
        doc_types = {}
        for doc in all_docs:
            doc_type = doc.get("document_type", "UNKNOWN")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        report = f"""
📋 DOCUMENT INTELLIGENCE TRIAGE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{"=" * 70}

📊 PORTFOLIO OVERVIEW
• Total Jobs Scanned: {len(all_job_results)}
• Total Documents: {len(all_docs)}
• Critical Documents: {len(critical_docs)}
• Executed Contracts: {len(executed_contracts)}
• Primary Contracts: {len(primary_contracts)}
• Recommended for Full Analysis: {len(analyze_fully)}

📂 DOCUMENT TYPE BREAKDOWN
"""

        for doc_type, count in sorted(doc_types.items()):
            report += f"  • {doc_type}: {count}\n"

        report += f"""
🎯 IMMEDIATE ACTION ITEMS
"""

        # Priority 1: Critical executed contracts
        priority_1 = [
            d
            for d in all_docs
            if d.get("importance") == "CRITICAL"
            and d.get("status") == "EXECUTED_SIGNED"
        ]
        if priority_1:
            report += (
                f"\n🔥 PRIORITY 1: Critical Executed Contracts ({len(priority_1)})\n"
            )
            for doc in priority_1[:10]:  # Show top 10
                report += f"  • Job {doc['job_number']}: {doc['filename']}\n"
                report += f"    Summary: {doc.get('one_line_summary', 'N/A')}\n"

        # Priority 2: Primary contracts for full analysis
        priority_2 = [
            d for d in analyze_fully if d.get("document_type") == "PRIMARY_CONTRACT"
        ]
        if priority_2:
            report += (
                f"\n📋 PRIORITY 2: Primary Contracts for Analysis ({len(priority_2)})\n"
            )
            for doc in priority_2[:10]:  # Show top 10
                report += f"  • Job {doc['job_number']}: {doc['filename']}\n"
                report += f"    Summary: {doc.get('one_line_summary', 'N/A')}\n"

        # Priority 3: Documents needing manual review
        manual_review = [
            d for d in all_docs if d.get("recommendation") == "REVIEW_MANUALLY"
        ]
        if manual_review:
            report += f"\n👁️ PRIORITY 3: Manual Review Required ({len(manual_review)})\n"
            for doc in manual_review[:5]:  # Show top 5
                report += f"  • Job {doc['job_number']}: {doc['filename']}\n"
                report += f"    Reason: {doc.get('one_line_summary', 'Classification uncertain')}\n"

        report += f"""
📊 JOB-BY-JOB BREAKDOWN
"""

        for job in all_job_results:
            job_critical = len(
                [
                    d
                    for d in job["scanned_documents"]
                    if d.get("importance") == "CRITICAL"
                ]
            )
            job_primary = len(
                [
                    d
                    for d in job["scanned_documents"]
                    if d.get("document_type") == "PRIMARY_CONTRACT"
                ]
            )

            report += f"\n  📁 Job {job['job_number']}: {job_critical} critical, {job_primary} primary contracts\n"

            # Show the most important document in this job
            job_docs = job["scanned_documents"]
            if job_docs:
                # Find the most important document
                best_doc = max(
                    job_docs,
                    key=lambda d: (
                        d.get("importance") == "CRITICAL",
                        d.get("status") == "EXECUTED_SIGNED",
                        d.get("document_type") == "PRIMARY_CONTRACT",
                    ),
                )

                if best_doc.get("importance") in ["CRITICAL", "HIGH"]:
                    report += f"    🌟 Main Document: {best_doc['filename']}\n"
                    report += f"       {best_doc.get('one_line_summary', 'N/A')}\n"

        return report

    def scan_all_jobs(self):
        """Scan all job directories"""

        job_dirs = [
            d
            for d in self.contracts_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        # Sort by job number
        def extract_job_number(path):
            try:
                return int(path.name[:4])
            except:
                return 9999

        job_dirs = sorted(job_dirs, key=extract_job_number)

        print(f"🔍 Starting document intelligence scan")
        print(f"📁 Contract directory: {self.contracts_dir}")
        print(f"🎯 Jobs to scan: {len(job_dirs)}")

        all_job_results = []
        start_time = time.time()

        for i, job_dir in enumerate(job_dirs, 1):
            print(f"\n📊 Job {i}/{len(job_dirs)}")

            try:
                job_result = self.scan_job_directory(job_dir)
                all_job_results.append(job_result)

                # Save cache periodically
                if i % 5 == 0:
                    self.save_scan_cache()

            except KeyboardInterrupt:
                print("\n⏹️ Scan interrupted by user")
                break
            except Exception as e:
                print(f"❌ Job scan failed: {e}")
                continue

        # Final save
        self.save_scan_cache()

        # Generate and save triage report
        report = self.generate_triage_report(all_job_results)

        # Save results and report
        results_file = self.contracts_dir / "document_triage_results.json"
        with open(results_file, "w") as f:
            json.dump(all_job_results, f, indent=2, default=str)

        report_file = self.contracts_dir / "document_triage_report.txt"
        with open(report_file, "w") as f:
            f.write(report)

        elapsed_time = time.time() - start_time

        print(f"\n⏱️ Scan completed in {elapsed_time/60:.1f} minutes")
        print(f"📋 Triage report saved to: {report_file}")
        print(f"📊 Detailed results saved to: {results_file}")
        print("\n" + report)


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python document_intelligence_scanner.py /path/to/SAMPLE_CONTRACTS/"
        )
        sys.exit(1)

    contracts_directory = sys.argv[1]

    if not os.path.exists(contracts_directory):
        print(f"❌ Directory not found: {contracts_directory}")
        sys.exit(1)

    print("🔍 DOCUMENT INTELLIGENCE SCANNER")
    print("=" * 50)
    print(f"📁 Target Directory: {contracts_directory}")
    print(f"🤖 AI Provider: Claude (Anthropic)")
    print(f"💰 Estimated Cost: ~$0.01-0.03 per document")
    print(f"⚡ Speed: ~15-30 seconds per document")

    # Confirm before proceeding
    response = input("\nProceed with document scan? (y/N): ")
    if response.lower() != "y":
        print("Cancelled.")
        sys.exit(0)

    scanner = DocumentIntelligenceScanner(contracts_directory)
    scanner.scan_all_jobs()


if __name__ == "__main__":
    main()
