import pydantic

class Post(pydantic.BaseModel):
    id: str
    post_type: str
    post_url: str
    title: str
    address: str
    description: str
    square: int
    photo_url: str
    price: int
    locale: str