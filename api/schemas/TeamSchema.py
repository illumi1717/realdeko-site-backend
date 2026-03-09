from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TeamMemberCreate(BaseModel):
    name: str
    position: str
    bio: str
    image_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    order: Optional[int] = None


class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    bio: Optional[str] = None
    image_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    order: Optional[int] = None


class TeamMemberResponse(BaseModel):
    id: str
    name: str
    position: str
    bio: str
    image_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    order: int
    created_at: datetime
    updated_at: datetime
