from fastapi import APIRouter
from api.schemas.ApplicationSchema import ApplicationSchema
from telegram_bot.initialize import send_telegram_message

router = APIRouter()

@router.post("/application")
def create_application(application: ApplicationSchema):
    send_telegram_message(f"Нова заявка:\n\n{application.name}\n\n{application.phone}\n\n{application.message}")
    return {"message": "Application created successfully"}