from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from api.dependencies.auth import require_admin
from api.schemas.ApplicationSchema import ApplicationSchema, ApplicationStatusUpdate, ApplicationNotesUpdate
from dbase.collections.ApplicationCollection import ApplicationCollection
from email_service.seznam_service import send_realdekogroup_email

router = APIRouter()

applications_db = ApplicationCollection()


@router.post("/application")
def create_application(application: ApplicationSchema):
    """Save application to DB and send email notification."""
    data = application.model_dump()
    saved = applications_db.create(data)

    # Send email notification (non-blocking: don't fail the request if email fails)
    try:
        send_realdekogroup_email(
            name=application.name,
            phone=application.phone,
            message=application.message,
        )
    except Exception as e:
        print(f"Failed to send email notification: {e}")

    return JSONResponse(status_code=201, content={"message": "Application created successfully", "id": saved["id"]})


@router.get("/applications")
def list_applications(status: Optional[str] = None, _admin: dict = Depends(require_admin)):
    """List all applications, optionally filtered by status."""
    items = applications_db.list(status=status)
    return items


@router.get("/applications/{application_id}")
def get_application(application_id: str, _admin: dict = Depends(require_admin)):
    """Get a single application by ID."""
    item = applications_db.get(application_id)
    if not item:
        raise HTTPException(status_code=404, detail="Application not found")
    return item


@router.patch("/applications/{application_id}/status")
def update_application_status(application_id: str, body: ApplicationStatusUpdate, _admin: dict = Depends(require_admin)):
    """Update the status of an application (new -> processed, etc.)."""
    if body.status not in ("new", "processed"):
        raise HTTPException(status_code=400, detail="Status must be 'new' or 'processed'")

    updated = applications_db.update_status(application_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return updated


@router.patch("/applications/{application_id}/notes")
def update_application_notes(application_id: str, body: ApplicationNotesUpdate, _admin: dict = Depends(require_admin)):
    """Update admin notes for an application."""
    updated = applications_db.update_notes(application_id, body.notes)
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return updated


@router.delete("/applications/{application_id}")
def delete_application(application_id: str, _admin: dict = Depends(require_admin)):
    """Delete an application."""
    deleted = applications_db.delete(application_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"message": "Application deleted"}
