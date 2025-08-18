from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import csv
import io
import traceback
import logging
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User as UserModel
from app.models.wip import WIP as WIPModel
from app.schemas.wip import WIP as WIPSchema

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wip", tags=["WIP"])


@router.get("/", response_model=List[WIPSchema])
def get_wip_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Get all WIP items - requires authentication."""
    try:
        logger.info(f"Getting WIP items for user: {current_user.username}")
        wip_items = db.query(WIPModel).offset(skip).limit(limit).all()
        logger.info(f"Found {len(wip_items)} WIP items")
        return wip_items
    except Exception as e:
        logger.error(f"Error getting WIP items: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/upload-csv")
def upload_wip_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Upload WIP items from CSV file - requires authentication."""

    logger.info(f"CSV upload started by user: {current_user.username}")
    logger.info(f"File: {file.filename}, Content-Type: {file.content_type}")

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV file")

    try:
        # Read the CSV file
        logger.info("Reading CSV file...")
        contents = file.file.read()
        csv_data = contents.decode("utf-8")
        csv_file = io.StringIO(csv_data)

        # Parse CSV
        logger.info("Parsing CSV...")
        csv_reader = csv.DictReader(csv_file)

        # Validate headers
        expected_headers = {"job_number", "project_name"}
        actual_headers = set(csv_reader.fieldnames) if csv_reader.fieldnames else set()

        logger.info(f"Expected headers: {expected_headers}")
        logger.info(f"Actual headers: {actual_headers}")

        if not expected_headers.issubset(actual_headers):
            missing_headers = expected_headers - actual_headers
            error_msg = f"CSV missing required headers: {', '.join(missing_headers)}. Found headers: {', '.join(actual_headers) if actual_headers else 'None'}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # Process CSV rows
        created_items = []
        errors = []

        logger.info("Processing CSV rows...")
        for row_num, row in enumerate(csv_reader, start=1):
            try:
                # Clean and validate data
                job_number = row.get("job_number", "").strip()
                project_name = row.get("project_name", "").strip()

                logger.info(
                    f"Row {row_num}: job_number='{job_number}', project_name='{project_name}'"
                )

                if not job_number or not project_name:
                    error_msg = f"Row {row_num}: Missing job_number or project_name"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue

                # Check if job_number already exists
                existing_item = (
                    db.query(WIPModel).filter(WIPModel.job_number == job_number).first()
                )

                if existing_item:
                    error_msg = (
                        f"Row {row_num}: Job number '{job_number}' already exists"
                    )
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue

                # Create new WIP item
                logger.info(f"Creating WIP item: {job_number} - {project_name}")
                wip_item = WIPModel(job_number=job_number, project_name=project_name)

                db.add(wip_item)
                created_items.append(
                    {"job_number": job_number, "project_name": project_name}
                )

            except Exception as e:
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                logger.error(traceback.format_exc())

        # Commit all changes if there are any successful items
        if created_items:
            logger.info(f"Committing {len(created_items)} items to database...")
            db.commit()
            logger.info("Database commit successful")

        result = {
            "message": f"Successfully processed {len(created_items)} items",
            "created_count": len(created_items),
            "error_count": len(errors),
            "created_items": created_items,
            "errors": errors if errors else None,
        }

        logger.info(f"Upload complete: {result['message']}")
        return result

    except HTTPException:
        # Re-raise HTTP exceptions (they're already handled)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during CSV upload: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error processing CSV file: {str(e)}"
        )
    finally:
        try:
            file.file.close()
        except:
            pass


@router.get("/template")
def download_csv_template(current_user: UserModel = Depends(get_current_active_user)):
    """Download CSV template for WIP upload."""
    try:
        logger.info(f"Template download requested by user: {current_user.username}")
        from fastapi.responses import Response

        # Create CSV template
        template_content = "job_number,project_name\nJOB-001,Sample Project Name\nJOB-002,Another Project Example\n"

        return Response(
            content=template_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=wip_template.csv"},
        )
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error generating template: {str(e)}"
        )


@router.delete("/clear-all")
def clear_all_wip_items(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user),
):
    """Clear all WIP items - requires authentication."""
    try:
        logger.info(f"Clear all WIP items requested by user: {current_user.username}")
        deleted_count = db.query(WIPModel).count()
        db.query(WIPModel).delete()
        db.commit()

        result = {
            "message": f"Deleted {deleted_count} WIP items",
            "deleted_count": deleted_count,
        }

        logger.info(f"Cleared all WIP items: {result['message']}")
        return result
    except Exception as e:
        logger.error(f"Error clearing WIP items: {str(e)}")
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error clearing WIP items: {str(e)}"
        )
