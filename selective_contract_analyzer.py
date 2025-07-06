#!/usr/bin/env python3
"""
Selective Contract Analyzer
Performs full analysis only on documents you choose based on triage results

Usage:
    python selective_contract_analyzer.py /path/to/SAMPLE_CONTRACTS/

Features:
- Uses triage results to show document options
- Interactive selection of documents for full analysis
- Batch processing of selected contracts
- Integration with encrypted database
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.pdf_extractor import extract_text_from_pdf
from app.services.claude_contract_analyzer import ComprehensiveClaudeAnalyzer


class SelectiveContractAnalyzer:
    """
    Analyze only selected contracts based on triage results
    """

    def __init__(self, contracts_directory: str):
        self.contracts_dir = Path(contracts_directory)
        self.analyzer = ComprehensiveClaudeAnalyzer()

        # Load triage results
        self.triage_file = self.contracts_dir / "document_triage_results.json"
        self.triage_data = self.load_triage_results()

        if not self.triage_data:
            raise Exception(
                "No triage results found. Run document_intelligence_scanner.py first."
            )

    def load_triage_results(self) -> List[Dict]:
        """Load previous triage results"""
        if not self.triage_file.exists():
            return None

        try:
            with open(self.triage_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Could not load triage results: {e}")
            return None

    def get_recommended_documents(self) -> List[Dict]:
        """Get documents recommended for full analysis"""
        recommended = []

        for job in self.triage_data:
            for doc in job["scanned_documents"]:
                if (
                    doc.get("recommendation") == "ANALYZE_FULLY"
                    or doc.get("importance") == "CRITICAL"
                ):
                    doc["job_number"] = job["job_number"]
                    doc["job_name"] = job["job_name"]
                    recommended.append(doc)

        return recommended

    def get_primary_contracts_by_job(self) -> Dict[str, List[Dict]]:
        """Get primary contracts organized by job"""
        by_job = {}

        for job in self.triage_data:
            job_num = job["job_number"]
            by_job[job_num] = {"job_name": job["job_name"], "documents": []}

            for doc in job["scanned_documents"]:
                # Include primary contracts and critical documents
                if (
                    doc.get("document_type") == "PRIMARY_CONTRACT"
                    or doc.get("importance") == "CRITICAL"
                    or doc.get("status") == "EXECUTED_SIGNED"
                ):

                    doc["job_number"] = job["job_number"]
                    doc["job_name"] = job["job_name"]
                    by_job[job_num]["documents"].append(doc)

        return by_job

    def display_selection_menu(self) -> List[Dict]:
        """Interactive menu to select documents for analysis"""

        print("\n📋 DOCUMENT SELECTION MENU")
        print("=" * 50)

        # Option 1: Recommended documents
        recommended = self.get_recommended_documents()
        print(f"\n1️⃣ Analyze Recommended Documents ({len(recommended)} documents)")
        print("   Documents that the AI recommends for full analysis")

        # Option 2: Job-by-job selection
        by_job = self.get_primary_contracts_by_job()
        jobs_with_docs = {k: v for k, v in by_job.items() if v["documents"]}

        print(f"\n2️⃣ Select by Job ({len(jobs_with_docs)} jobs available)")
        print("   Choose specific jobs to analyze")

        # Option 3: Custom selection
        print(f"\n3️⃣ Custom Document Selection")
        print("   Pick individual documents across all jobs")

        print(f"\n4️⃣ Exit")

        while True:
            choice = input("\nSelect option (1-4): ").strip()

            if choice == "1":
                return self.confirm_recommended_selection(recommended)
            elif choice == "2":
                return self.select_by_job(jobs_with_docs)
            elif choice == "3":
                return self.custom_document_selection()
            elif choice == "4":
                return []
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")

    def confirm_recommended_selection(self, recommended: List[Dict]) -> List[Dict]:
        """Show recommended documents and confirm"""

        print(f"\n📋 RECOMMENDED DOCUMENTS ({len(recommended)})")
        print("=" * 50)

        for i, doc in enumerate(recommended, 1):
            print(f"\n{i:2d}. Job {doc['job_number']}: {doc['filename']}")
            print(f"    Type: {doc.get('document_type', 'Unknown')}")
            print(f"    Importance: {doc.get('importance', 'Unknown')}")
            print(f"    Summary: {doc.get('one_line_summary', 'N/A')}")

        print(f"\n💰 Estimated cost: ${len(recommended) * 0.10:.2f}")
        print(f"⏱️ Estimated time: {len(recommended) * 2:.0f} minutes")

        confirm = input(
            f"\nAnalyze all {len(recommended)} recommended documents? (y/N): "
        )

        if confirm.lower() == "y":
            return recommended
        else:
            return []

    def select_by_job(self, by_job: Dict) -> List[Dict]:
        """Select entire jobs for analysis"""

        print(f"\n📁 JOB SELECTION")
        print("=" * 50)

        job_list = list(by_job.keys())

        for i, job_num in enumerate(job_list, 1):
            job_data = by_job[job_num]
            doc_count = len(job_data["documents"])

            print(f"{i:2d}. Job {job_num}: {job_data['job_name']}")
            print(f"    Documents: {doc_count}")

            # Show key document types
            doc_types = {}
            for doc in job_data["documents"]:
                doc_type = doc.get("document_type", "Unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            print(
                f"    Types: {', '.join([f'{k}({v})' for k, v in doc_types.items()])}"
            )

        print(f"\n{len(job_list)+1}. Select All Jobs")
        print(f"{len(job_list)+2}. Back to Main Menu")

        while True:
            choice = input(
                f"\nSelect jobs (comma-separated numbers, or single number): "
            ).strip()

            if choice == str(len(job_list) + 2):  # Back to menu
                return []

            try:
                if choice == str(len(job_list) + 1):  # All jobs
                    selected_jobs = list(range(1, len(job_list) + 1))
                else:
                    selected_jobs = [int(x.strip()) for x in choice.split(",")]

                # Validate selections
                if all(1 <= num <= len(job_list) for num in selected_jobs):
                    selected_docs = []

                    for job_index in selected_jobs:
                        job_num = job_list[job_index - 1]
                        selected_docs.extend(by_job[job_num]["documents"])

                    print(
                        f"\n✅ Selected {len(selected_docs)} documents from {len(selected_jobs)} jobs"
                    )
                    print(f"💰 Estimated cost: ${len(selected_docs) * 0.10:.2f}")

                    confirm = input("Proceed with analysis? (y/N): ")
                    if confirm.lower() == "y":
                        return selected_docs
                    else:
                        return []
                else:
                    print("❌ Invalid job numbers. Please try again.")

            except ValueError:
                print("❌ Invalid input. Please enter numbers separated by commas.")

    def custom_document_selection(self) -> List[Dict]:
        """Custom document selection across all jobs"""

        print(f"\n📄 CUSTOM DOCUMENT SELECTION")
        print("=" * 50)
        print("Showing important documents across all jobs...")

        # Collect all important documents
        all_docs = []
        for job in self.triage_data:
            for doc in job["scanned_documents"]:
                # Only show documents worth analyzing
                if (
                    doc.get("importance") in ["CRITICAL", "HIGH"]
                    or doc.get("document_type") == "PRIMARY_CONTRACT"
                    or doc.get("status") == "EXECUTED_SIGNED"
                ):

                    doc["job_number"] = job["job_number"]
                    doc["job_name"] = job["job_name"]
                    all_docs.append(doc)

        # Sort by job number
        all_docs.sort(key=lambda x: x["job_number"])

        for i, doc in enumerate(all_docs, 1):
            print(f"\n{i:2d}. Job {doc['job_number']}: {doc['filename']}")
            print(
                f"    Type: {doc.get('document_type', 'Unknown')} | Importance: {doc.get('importance', 'Unknown')}"
            )
            print(f"    Summary: {doc.get('one_line_summary', 'N/A')}")

        print(f"\nEnter document numbers to analyze (comma-separated):")
        print(f"Example: 1,3,5-8,12  (ranges supported)")

        while True:
            choice = input(f"\nDocument numbers (or 'back' to return): ").strip()

            if choice.lower() == "back":
                return []

            try:
                selected_indices = self.parse_number_ranges(choice, len(all_docs))

                if selected_indices:
                    selected_docs = [all_docs[i - 1] for i in selected_indices]

                    print(f"\n✅ Selected {len(selected_docs)} documents")
                    for doc in selected_docs:
                        print(f"  • Job {doc['job_number']}: {doc['filename']}")

                    print(f"\n💰 Estimated cost: ${len(selected_docs) * 0.10:.2f}")

                    confirm = input("Proceed with analysis? (y/N): ")
                    if confirm.lower() == "y":
                        return selected_docs
                    else:
                        return []
                else:
                    print("❌ No valid selections made.")

            except Exception as e:
                print(f"❌ Invalid input: {e}")

    def parse_number_ranges(self, input_str: str, max_num: int) -> List[int]:
        """Parse number ranges like '1,3,5-8,12'"""
        numbers = set()

        for part in input_str.split(","):
            part = part.strip()

            if "-" in part:
                # Handle ranges like '5-8'
                start, end = part.split("-", 1)
                start, end = int(start.strip()), int(end.strip())

                if 1 <= start <= max_num and 1 <= end <= max_num and start <= end:
                    numbers.update(range(start, end + 1))
                else:
                    raise ValueError(f"Invalid range: {part}")
            else:
                # Handle single numbers
                num = int(part)
                if 1 <= num <= max_num:
                    numbers.add(num)
                else:
                    raise ValueError(f"Number out of range: {num}")

        return sorted(list(numbers))

    def analyze_selected_documents(self, selected_docs: List[Dict]) -> List[Dict]:
        """Perform full analysis on selected documents"""

        print(f"\n🚀 STARTING FULL ANALYSIS")
        print("=" * 50)
        print(f"Documents to analyze: {len(selected_docs)}")

        results = []

        for i, doc in enumerate(selected_docs, 1):
            print(f"\n📄 Analyzing ({i}/{len(selected_docs)}): {doc['filename']}")
            print(f"   Job {doc['job_number']}: {doc['job_name']}")

            try:
                # Extract full text
                print("   📖 Extracting full text...")
                file_path = Path(doc["file_path"])
                contract_text = extract_text_from_pdf(str(file_path))

                if not contract_text or len(contract_text.strip()) < 100:
                    raise Exception("Insufficient text extracted")

                print(f"   ✅ Extracted {len(contract_text)} characters")

                # Full analysis with Claude
                print("   🤖 Performing comprehensive analysis...")
                analysis_result = self.analyzer.analyze_contract(contract_text)

                if analysis_result["success"]:
                    result = {
                        "filename": doc["filename"],
                        "file_path": doc["file_path"],
                        "job_number": doc["job_number"],
                        "job_name": doc["job_name"],
                        "document_classification": {
                            "type": doc.get("document_type"),
                            "importance": doc.get("importance"),
                            "status": doc.get("status"),
                            "summary": doc.get("one_line_summary"),
                        },
                        "text_length": len(contract_text),
                        "analysis": analysis_result["data"],
                        "fields_extracted": analysis_result.get("fields_extracted", 0),
                        "analysis_quality": (
                            "excellent"
                            if analysis_result.get("fields_extracted", 0) > 12
                            else "good"
                        ),
                        "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }

                    results.append(result)

                    # Show key results
                    data = analysis_result["data"]
                    print(f"   💰 Contract Value: ${data.get('contract_value', 'N/A')}")
                    print(f"   🏢 Contractor: {data.get('contractor_name', 'N/A')}")
                    print(f"   📋 Project: {data.get('contract_name', 'N/A')}")
                    print(
                        f"   📊 Data Quality: {analysis_result.get('fields_extracted', 0)}/18 fields"
                    )

                else:
                    raise Exception("Analysis failed")

            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")

                error_result = {
                    "filename": doc["filename"],
                    "file_path": doc["file_path"],
                    "job_number": doc["job_number"],
                    "job_name": doc["job_name"],
                    "error": str(e),
                    "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                results.append(error_result)

            # Respectful delay
            time.sleep(1)

        return results

    def save_analysis_results(self, results: List[Dict]):
        """Save analysis results to files"""

        # Save detailed results
        results_file = self.contracts_dir / "selected_analysis_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Generate executive summary
        successful_analyses = [r for r in results if "analysis" in r]
        failed_analyses = [r for r in results if "error" in r]

        total_value = 0
        contractors = set()

        for result in successful_analyses:
            analysis = result.get("analysis", {})
            if analysis.get("contract_value"):
                try:
                    total_value += float(analysis["contract_value"])
                except:
                    pass

            if analysis.get("contractor_name"):
                contractors.add(analysis["contractor_name"])

        summary_report = f"""
📊 SELECTIVE ANALYSIS SUMMARY
Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
{"=" * 60}

📈 ANALYSIS RESULTS
• Documents Analyzed: {len(results)}
• Successful Analyses: {len(successful_analyses)}
• Failed Analyses: {len(failed_analyses)}
• Success Rate: {(len(successful_analyses)/len(results)*100):.1f}%

💰 FINANCIAL SUMMARY
• Total Contract Value: ${total_value:,.2f}
• Average Contract Value: ${(total_value/len(successful_analyses) if successful_analyses else 0):,.2f}
• Unique Contractors: {len(contractors)}

📋 ANALYZED CONTRACTS
"""

        for result in successful_analyses:
            analysis = result.get("analysis", {})
            value = analysis.get("contract_value", 0)

            summary_report += f"""
  📄 {result['filename']}
      Job: {result['job_number']} - {result['job_name']}
      Value: ${value:,.2f if value else 0}
      Contractor: {analysis.get('contractor_name', 'N/A')}
      Project: {analysis.get('contract_name', 'N/A')}
      Quality: {result.get('fields_extracted', 0)}/18 fields extracted
"""

        if failed_analyses:
            summary_report += f"""
❌ FAILED ANALYSES ({len(failed_analyses)})
"""
            for result in failed_analyses:
                summary_report += f"  • {result['filename']}: {result.get('error', 'Unknown error')}\n"

        summary_report += f"""
💡 NEXT STEPS
1. Review the detailed results in: {results_file.name}
2. Consider uploading successful analyses to your encrypted database
3. Manually review any failed analyses
4. Use the financial data for project planning and budgeting

📁 Files Generated:
• Detailed Results: {results_file.name}
• Summary Report: selected_analysis_summary.txt
"""

        # Save summary report
        summary_file = self.contracts_dir / "selected_analysis_summary.txt"
        with open(summary_file, "w") as f:
            f.write(summary_report)

        print(f"\n📊 Analysis complete!")
        print(f"📋 Summary saved to: {summary_file}")
        print(f"📊 Detailed results saved to: {results_file}")
        print(summary_report)

    def run_selective_analysis(self):
        """Main method to run selective analysis"""

        print(f"🎯 SELECTIVE CONTRACT ANALYZER")
        print("=" * 50)
        print(f"📁 Contract Directory: {self.contracts_dir}")
        print(f"📋 Triage Data Loaded: {len(self.triage_data)} jobs")

        # Show triage summary
        total_docs = sum(len(job["scanned_documents"]) for job in self.triage_data)
        recommended_docs = len(self.get_recommended_documents())

        print(f"📊 Total Documents Available: {total_docs}")
        print(f"🎯 AI Recommended for Analysis: {recommended_docs}")

        # Interactive selection
        selected_docs = self.display_selection_menu()

        if not selected_docs:
            print("\n👋 No documents selected. Exiting.")
            return

        print(f"\n🚀 Ready to analyze {len(selected_docs)} documents")
        print(f"💰 Estimated cost: ${len(selected_docs) * 0.10:.2f}")
        print(f"⏱️ Estimated time: {len(selected_docs) * 2:.0f} minutes")

        final_confirm = input("\nProceed with full analysis? (y/N): ")
        if final_confirm.lower() != "y":
            print("👋 Analysis cancelled.")
            return

        # Perform analysis
        results = self.analyze_selected_documents(selected_docs)

        # Save results and generate report
        self.save_analysis_results(results)


def main():
    if len(sys.argv) != 2:
        print("Usage: python selective_contract_analyzer.py /path/to/SAMPLE_CONTRACTS/")
        print(
            "\nNote: Run document_intelligence_scanner.py first to generate triage data."
        )
        sys.exit(1)

    contracts_directory = sys.argv[1]

    if not os.path.exists(contracts_directory):
        print(f"❌ Directory not found: {contracts_directory}")
        sys.exit(1)

    try:
        analyzer = SelectiveContractAnalyzer(contracts_directory)
        analyzer.run_selective_analysis()

    except Exception as e:
        print(f"❌ Error: {e}")
        if "No triage results found" in str(e):
            print("\n💡 Solution: Run the document scanner first:")
            print("python document_intelligence_scanner.py /path/to/SAMPLE_CONTRACTS/")
        sys.exit(1)


if __name__ == "__main__":
    main()
