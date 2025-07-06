#!/usr/bin/env python3
"""
Single Job Scanner - Test the workflow on one project first
Perfect for testing before scaling to full portfolio

Usage:
    python single_job_scanner.py "/path/to/job/directory"

Example:
    python single_job_scanner.py "/Users/ryze.ai/Desktop/SAMPLE_CONTRACTS/2315 - Rte 395 CT Bridge Metallizing (19)- Blast All"
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.pdf_extractor import extract_text_from_pdf
from app.services.claude_contract_analyzer import ComprehensiveClaudeAnalyzer
from app.core.config import settings


class SingleJobAnalyzer:
    """
    Test analyzer for one job directory
    """

    def __init__(self, job_directory: str):
        self.job_dir = Path(job_directory)

        if not self.job_dir.exists():
            raise Exception(f"Job directory not found: {job_directory}")

        self.job_name = self.job_dir.name
        self.job_number = self.job_name[:4] if len(self.job_name) >= 4 else "UNKNOWN"

        # Results storage
        self.results_file = self.job_dir / f"analysis_results_{self.job_number}.json"

        print(f"🎯 Single Job Analyzer")
        print(f"📁 Job: {self.job_name}")
        print(f"📊 Number: {self.job_number}")

    def quick_classify_document(self, document_text: str, filename: str) -> Dict:
        """Quick document classification"""

        text_sample = document_text[:2000]

        prompt = f"""
        Quickly analyze this CONSTRUCTION contract document and classify it.
        
        FILENAME: {filename}
        JOB: {self.job_name}
        
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
                return self.parse_response(result["content"][0]["text"], filename)
            else:
                raise Exception(f"API error: {response.status_code}")

        except Exception as e:
            return {
                "filename": filename,
                "error": str(e),
                "document_type": "ERROR",
                "recommendation": "REVIEW_MANUALLY",
            }

    def parse_response(self, response: str, filename: str) -> Dict:
        """Parse Claude's response"""

        result = {"filename": filename}

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

    def scan_all_documents(self) -> List[Dict]:
        """Scan all PDFs in the job directory"""

        pdf_files = list(self.job_dir.glob("*.pdf"))

        if not pdf_files:
            print("❌ No PDF files found in directory")
            return []

        print(f"\n🔍 Found {len(pdf_files)} PDF files to scan")
        print("=" * 60)

        scanned_docs = []
        total_cost = 0

        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n📄 Scanning ({i}/{len(pdf_files)}): {pdf_file.name}")

            try:
                # Extract text
                print("   📖 Extracting text...")
                document_text = extract_text_from_pdf(str(pdf_file))

                if not document_text or len(document_text.strip()) < 50:
                    raise Exception("Insufficient text extracted")

                print(f"   ✅ Extracted {len(document_text)} characters")

                # Quick classify
                print("   🤖 Classifying document...")
                classification = self.quick_classify_document(
                    document_text, pdf_file.name
                )

                # Add metadata
                classification.update(
                    {
                        "file_path": str(pdf_file),
                        "file_size_kb": pdf_file.stat().st_size // 1024,
                        "text_length": len(document_text),
                        "scan_date": datetime.now().isoformat(),
                    }
                )

                scanned_docs.append(classification)
                total_cost += 0.02  # Rough estimate

                # Show results
                if "error" not in classification:
                    print(
                        f"   📋 Type: {classification.get('document_type', 'Unknown')}"
                    )
                    print(
                        f"   ⭐ Importance: {classification.get('importance', 'Unknown')}"
                    )
                    print(f"   💡 {classification.get('summary', 'No summary')}")
                    print(
                        f"   🎯 Recommendation: {classification.get('recommendation', 'Unknown')}"
                    )
                else:
                    print(f"   ❌ Error: {classification['error']}")

            except Exception as e:
                error_doc = {
                    "filename": pdf_file.name,
                    "file_path": str(pdf_file),
                    "error": str(e),
                    "scan_date": datetime.now().isoformat(),
                }
                scanned_docs.append(error_doc)
                print(f"   ❌ Failed: {e}")

            # Small delay
            time.sleep(0.5)

        print(f"\n💰 Estimated scan cost: ${total_cost:.2f}")
        return scanned_docs

    def generate_job_report(self, scanned_docs: List[Dict]) -> str:
        """Generate report for this job"""

        successful_scans = [d for d in scanned_docs if "error" not in d]
        failed_scans = [d for d in scanned_docs if "error" in d]

        # Categorize documents
        critical_docs = [
            d for d in successful_scans if d.get("importance") == "CRITICAL"
        ]
        primary_contracts = [
            d for d in successful_scans if d.get("document_type") == "PRIMARY_CONTRACT"
        ]
        executed_docs = [
            d for d in successful_scans if d.get("status") == "EXECUTED_SIGNED"
        ]
        analyze_recommendations = [
            d for d in successful_scans if d.get("recommendation") == "ANALYZE_FULLY"
        ]

        report = f"""
🎯 SINGLE JOB ANALYSIS REPORT
Job: {self.job_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{"=" * 70}

📊 SCAN SUMMARY
• Total Documents: {len(scanned_docs)}
• Successful Scans: {len(successful_scans)}
• Failed Scans: {len(failed_scans)}
• Success Rate: {(len(successful_scans)/len(scanned_docs)*100):.1f}%

📋 DOCUMENT CLASSIFICATION
• Critical Documents: {len(critical_docs)}
• Primary Contracts: {len(primary_contracts)}
• Executed Documents: {len(executed_docs)}
• Recommended for Full Analysis: {len(analyze_recommendations)}

🎯 PRIORITY DOCUMENTS
"""

        # Show most important documents
        priority_docs = sorted(
            successful_scans,
            key=lambda x: (
                x.get("importance") == "CRITICAL",
                x.get("document_type") == "PRIMARY_CONTRACT",
                x.get("status") == "EXECUTED_SIGNED",
            ),
            reverse=True,
        )

        for i, doc in enumerate(priority_docs[:5], 1):
            report += f"""
  {i}. {doc['filename']}
     Type: {doc.get('document_type', 'Unknown')}
     Importance: {doc.get('importance', 'Unknown')}
     Status: {doc.get('status', 'Unknown')}
     Summary: {doc.get('summary', 'No summary available')}
     Recommendation: {doc.get('recommendation', 'Unknown')}
"""

        if analyze_recommendations:
            report += f"""
🚀 NEXT STEPS - RECOMMENDED FOR FULL ANALYSIS
"""
            for doc in analyze_recommendations:
                report += f"  • {doc['filename']} - {doc.get('summary', 'Primary document')}\n"

            cost_estimate = len(analyze_recommendations) * 0.10
            time_estimate = len(analyze_recommendations) * 2

            report += f"""
💰 Full Analysis Cost Estimate: ${cost_estimate:.2f}
⏱️ Full Analysis Time Estimate: {time_estimate} minutes

To run full analysis on recommended documents:
python selective_contract_analyzer.py "{self.job_dir}"
"""

        if failed_scans:
            report += f"""
❌ FAILED DOCUMENTS ({len(failed_scans)})
"""
            for doc in failed_scans:
                report += (
                    f"  • {doc['filename']}: {doc.get('error', 'Unknown error')}\n"
                )

        return report

    def run_analysis(self):
        """Run the complete single job analysis"""

        print(f"🚀 Starting analysis of job: {self.job_name}")

        # Verify API key
        if not settings.anthropic_api_key:
            print("❌ ANTHROPIC_API_KEY not configured")
            return

        # Scan all documents
        scanned_docs = self.scan_all_documents()

        if not scanned_docs:
            print("❌ No documents to analyze")
            return

        # Save results
        with open(self.results_file, "w") as f:
            json.dump(scanned_docs, f, indent=2, default=str)

        # Generate and save report
        report = self.generate_job_report(scanned_docs)

        report_file = self.job_dir / f"job_analysis_report_{self.job_number}.txt"
        with open(report_file, "w") as f:
            f.write(report)

        print(f"\n📊 Analysis complete!")
        print(f"📋 Report saved to: {report_file}")
        print(f"📊 Results saved to: {self.results_file}")
        print(report)


def main():
    if len(sys.argv) != 2:
        print('Usage: python single_job_scanner.py "/path/to/job/directory"')
        print("\nExample:")
        print(
            'python single_job_scanner.py "/Users/ryze.ai/Desktop/SAMPLE_CONTRACTS/2315 - Rte 395 CT Bridge Metallizing (19)- Blast All"'
        )
        sys.exit(1)

    job_directory = sys.argv[1]

    try:
        analyzer = SingleJobAnalyzer(job_directory)
        analyzer.run_analysis()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
