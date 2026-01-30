from pydantic import BaseModel

class ApplicationSchema(BaseModel):
    name: str
    phone: str
    email: str | None = None
    message: str
    service: str | None = None