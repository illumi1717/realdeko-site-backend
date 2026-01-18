from pydantic import BaseModel

class ApplicationSchema(BaseModel):
    name: str
    phone: str
    message: str