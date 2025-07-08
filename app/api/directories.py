# app/api/directories.py
"""
Directory Analysis API - Works like the single_job_scanner.py script
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path

from app.core.database import get_db
from app.api.auth import get_current_active_user
from app.models.user import User
from app.services.contract_intelligence_service import ContractIntelligenceService
from app.services.pdf_extractor import extract_text_from_pdf
from app.schemas.directories import (
    AnalyzeDirectoryRequest,
    DirectoryAnalysisResponse,
    RankedDocument,
)

router = APIRouter()


# Endpoint to get directory contents (for UI directory picker)
@router.post("/list-directory")
async def list_directory(
    request: AnalyzeDirectoryRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    List PDF files in a directory (for UI preview before analysis)
    """

    directory_path = Path(request.directory_path)

    if not directory_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    if not directory_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    pdf_files = list(directory_path.glob("*.pdf"))

    file_list = []
    for pdf_file in pdf_files:
        file_info = {
            "filename": pdf_file.name,
            "file_path": str(pdf_file),
            "file_size_kb": pdf_file.stat().st_size // 1024,
            "file_size_mb": round(pdf_file.stat().st_size / (1024 * 1024), 2),
        }
        file_list.append(file_info)

    # Sort by filename
    file_list.sort(key=lambda x: x["filename"])

    job_name = directory_path.name
    job_number = job_name[:4] if len(job_name) >= 4 else "UNKNOWN"

    return {
        "success": True,
        "directory_path": str(directory_path),
        "job_name": job_name,
        "job_number": job_number,
        "total_pdf_files": len(pdf_files),
        "files": file_list,
        "estimated_scan_cost": len(pdf_files) * 0.02,
        "estimated_scan_time_minutes": len(pdf_files) * 0.5,
    }


@router.post("/analyze-directory", response_model=DirectoryAnalysisResponse)
async def analyze_directory(
    request: AnalyzeDirectoryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Analyze all PDFs in a directory - works exactly like single_job_scanner.py

    Takes a directory path and:
    1. Finds all PDF files in the directory
    2. Extracts text from each PDF
    3. Classifies each document (type, importance, status)
    4. Identifies the main contract
    5. Ranks all documents by importance
    6. Returns actionable recommendations

    """

    directory_path = Path(request.directory_path)

    # Validate directory exists
    if not directory_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Directory not found: {request.directory_path}"
        )

    if not directory_path.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Path is not a directory: {request.directory_path}"
        )

    # Extract job info from directory name (like your script)
    job_name = directory_path.name
    job_number = job_name[:4] if len(job_name) >= 4 else "UNKNOWN"

    # Find all PDF files
    pdf_files = list(directory_path.glob("*.pdf"))

    if not pdf_files:
        raise HTTPException(status_code=404, detail="No PDF files found in directory")

    try:
        # Initialize intelligence service
        intelligence_service = ContractIntelligenceService()

        # Process all PDFs - exactly like your script
        classifications = []
        failed_files = []
        total_scan_cost = 0

        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                # Extract text - exactly like your script
                document_text = extract_text_from_pdf(str(pdf_file))

                if not document_text or len(document_text.strip()) < 50:
                    raise Exception("Insufficient text extracted")

                # Classify document - exactly like your script
                classification = intelligence_service.classify_document(
                    document_text, pdf_file.name
                )

                # Add metadata - exactly like your script
                classification.update(
                    {
                        "file_path": str(pdf_file),
                        "file_size_kb": pdf_file.stat().st_size // 1024,
                        "text_length": len(document_text),
                    }
                )

                classifications.append(classification)
                total_scan_cost += 0.02  # Same estimate as your script

            except Exception as e:
                failed_files.append(f"{pdf_file.name}: {str(e)}")
                continue

        if not classifications:
            raise HTTPException(
                status_code=422, detail="No documents could be processed"
            )

        # Get ranked document list - exactly like your script priority logic
        ranked_docs = intelligence_service.get_ranked_document_list(classifications)

        # Identify main contract - exactly like your script
        main_contract_data = intelligence_service.identify_main_contract(
            classifications
        )

        # Convert to response format
        ranked_documents = []
        main_contract = None

        for doc in ranked_docs:
            ranked_doc = RankedDocument(
                filename=doc["filename"],
                rank=doc["rank"],
                importance_score=doc["importance_score"],
                priority_level=doc["priority_level"],
                document_type=doc.get("document_type", "UNKNOWN"),
                importance=doc.get("importance", "MEDIUM"),
                status=doc.get("status", "UNKNOWN"),
                summary=doc.get("summary", ""),
                recommendation=doc.get("recommendation", "REVIEW_MANUALLY"),
                is_main_contract=doc.get("is_main_contract", False),
                ranking_reason=doc.get("ranking_reason"),
                file_path=doc.get("file_path", ""),
                text_length=doc.get("text_length", 0),
            )

            ranked_documents.append(ranked_doc)

            # Set main contract
            if doc.get("is_main_contract"):
                main_contract = ranked_doc

        # Calculate summary stats - exactly like your script
        critical_docs = [
            d for d in classifications if d.get("importance") == "CRITICAL"
        ]
        primary_contracts = [
            d for d in classifications if d.get("document_type") == "PRIMARY_CONTRACT"
        ]
        executed_docs = [
            d for d in classifications if d.get("status") == "EXECUTED_SIGNED"
        ]
        analyze_recommendations = [
            d for d in classifications if d.get("recommendation") == "ANALYZE_FULLY"
        ]

        recommended_files = [doc["filename"] for doc in analyze_recommendations]

        success_rate = (len(classifications) / len(pdf_files) * 100) if pdf_files else 0
        estimated_analysis_cost = len(analyze_recommendations) * 0.10
        estimated_analysis_time = len(analyze_recommendations) * 2

        return DirectoryAnalysisResponse(
            success=True,
            message=f"Successfully analyzed {len(classifications)} of {len(pdf_files)} documents. Main contract: {main_contract.filename if main_contract else 'Not identified'}",
            job_name=job_name,
            job_number=job_number,
            main_contract=main_contract,
            ranked_documents=ranked_documents,
            total_documents=len(pdf_files),
            successful_scans=len(classifications),
            failed_scans=len(failed_files),
            success_rate=success_rate,
            critical_documents=len(critical_docs),
            primary_contracts=len(primary_contracts),
            executed_documents=len(executed_docs),
            recommended_for_analysis=len(analyze_recommendations),
            estimated_scan_cost=total_scan_cost,
            estimated_analysis_cost=estimated_analysis_cost,
            estimated_analysis_time_minutes=estimated_analysis_time,
            recommended_files=recommended_files,
            failed_files=failed_files,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Directory analysis failed: {str(e)}"
        )


# Simple endpoint to just get the main contract from a directory
@router.post("/identify-main-contract-directory")
async def identify_main_contract_directory(
    request: AnalyzeDirectoryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Quick endpoint to just identify the main contract from a directory
    Returns just the main contract info
    """

    # Run the full analysis
    full_result = await analyze_directory(request, current_user, db)

    if full_result.success and full_result.main_contract:
        return {
            "success": True,
            "job_name": full_result.job_name,
            "job_number": full_result.job_number,
            "main_contract": {
                "filename": full_result.main_contract.filename,
                "file_path": full_result.main_contract.file_path,
                "importance_score": full_result.main_contract.importance_score,
                "ranking_reason": full_result.main_contract.ranking_reason,
                "document_type": full_result.main_contract.document_type,
                "summary": full_result.main_contract.summary,
            },
            "total_documents": full_result.total_documents,
            "confidence": (
                "HIGH" if full_result.main_contract.importance_score > 120 else "MEDIUM"
            ),
        }
    else:
        return {
            "success": False,
            "error": "Could not identify main contract",
            "job_name": full_result.job_name if full_result else "Unknown",
            "suggestion": "Review documents manually",
        }
