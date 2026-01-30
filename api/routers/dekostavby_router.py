from fastapi import APIRouter, HTTPException
from email_service.seznam_service import send_email
from api.schemas.ApplicationSchema import ApplicationSchema
from fastapi.responses import JSONResponse

dekostavby_router = APIRouter()

@dekostavby_router.post("/create_application")
def create_application(application: ApplicationSchema):
    if send_email(application.name, application.phone, application.email, application.service, application.message):
        return JSONResponse(status_code=200, content={"message": "Application created successfully"})
    else:
        raise HTTPException(status_code=500, detail="Failed to create application")
    