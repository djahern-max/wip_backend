#!/usr/bin/env python3
"""
Convert Single Job Results to Portfolio Format
Converts single job scan results to format expected by selective analyzer

Usage:
    python convert_single_job_results.py "/Users/ryze.ai/Desktop/SAMPLE_CONTRACTS/"
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime


def convert_single_job_to_portfolio_format(contracts_directory: str):
    """Convert single job results to portfolio triage format"""

    contracts_dir = Path(contracts_directory)

    # Find all single job result files
    job_results = []

    for job_dir in contracts_dir.iterdir():
        if not job_dir.is_dir() or job_dir.name.startswith("."):
            continue

        # Look for single job result files
        result_files = list(job_dir.glob("analysis_results_*.json"))

        if result_files:
            result_file = result_files[0]  # Take the first one found

            try:
                with open(result_file, "r") as f:
                    scanned_docs = json.load(f)

                # Convert to portfolio format
                job_number = job_dir.name[:4]
                job_name = job_dir.name

                job_summary = {
                    "job_number": job_number,
                    "job_name": job_name,
                    "job_directory": str(job_dir),
                    "total_documents": len(scanned_docs),
                    "scanned_documents": scanned_docs,
                    "critical_documents": len(
                        [d for d in scanned_docs if d.get("importance") == "CRITICAL"]
                    ),
                    "executed_contracts": len(
                        [
                            d
                            for d in scanned_docs
                            if d.get("status") == "EXECUTED_SIGNED"
                        ]
                    ),
                    "primary_contracts": len(
                        [
                            d
                            for d in scanned_docs
                            if d.get("document_type") == "PRIMARY_CONTRACT"
                        ]
                    ),
                    "scan_date": datetime.now().isoformat(),
                }

                job_results.append(job_summary)
                print(f"✅ Converted Job {job_number}: {len(scanned_docs)} documents")

            except Exception as e:
                print(f"❌ Failed to convert {result_file}: {e}")

    if job_results:
        # Save in portfolio format
        portfolio_file = contracts_dir / "document_triage_results.json"

        with open(portfolio_file, "w") as f:
            json.dump(job_results, f, indent=2, default=str)

        print(f"\n✅ Portfolio triage file created: {portfolio_file}")
        print(f"📊 Jobs converted: {len(job_results)}")

        # Show what's available for selection
        for job in job_results:
            recommended = [
                d
                for d in job["scanned_documents"]
                if d.get("recommendation") == "ANALYZE_FULLY"
            ]
            print(
                f"  • Job {job['job_number']}: {len(recommended)} docs recommended for analysis"
            )

        return True
    else:
        print("❌ No single job result files found")
        print("💡 Run single_job_scanner.py on a job directory first")
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: python convert_single_job_results.py /path/to/SAMPLE_CONTRACTS/")
        sys.exit(1)

    contracts_directory = sys.argv[1]

    if not os.path.exists(contracts_directory):
        print(f"❌ Directory not found: {contracts_directory}")
        sys.exit(1)

    print("🔄 Converting Single Job Results to Portfolio Format")
    print("=" * 60)

    success = convert_single_job_to_portfolio_format(contracts_directory)

    if success:
        print(f"\n🚀 Ready for selective analysis!")
        print(f'Run: python selective_contract_analyzer.py "{contracts_directory}"')
    else:
        print(f"\n❌ Conversion failed")


if __name__ == "__main__":
    main()
