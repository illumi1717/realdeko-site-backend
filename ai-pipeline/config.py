import pydantic
from typing import Literal

classifier_types = Literal['rent', 'sale']

localizer_types = Literal['ua', 'ru', 'en', 'cz']

class Post(pydantic.BaseModel):
    id: str
    post_type: classifier_types
    post_url: str
    title: str
    address: str
    description: str
    square: int
    photo_url: str
    price: int
    locale: localizer_types