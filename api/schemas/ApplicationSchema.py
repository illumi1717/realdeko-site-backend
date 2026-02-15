from pydantic import BaseModel
from typing import Optional


class ApplicationSchema(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    message: str
    service: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: str  # "new", "processed"
