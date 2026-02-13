from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


class KeyMetric(BaseModel):
    label: str
    value: str
    helper: Optional[str] = None


class GalleryImage(BaseModel):
    src: str
    alt: Optional[str] = None
    caption: Optional[str] = None


class HeadingBlock(BaseModel):
    type: Literal["heading"]
    level: Literal["h2", "h3"] = "h2"
    text: str


class TextBlock(BaseModel):
    type: Literal["text"]
    content: str


class GalleryBlock(BaseModel):
    type: Literal["gallery"]
    title: Optional[str] = None
    images: List[GalleryImage]


class VideoBlock(BaseModel):
    type: Literal["video"]
    title: Optional[str] = None
    url: str


class QuoteBlock(BaseModel):
    type: Literal["quote"]
    text: str
    author: Optional[str] = None
    role: Optional[str] = None


class StatsBlock(BaseModel):
    type: Literal["stats"]
    title: Optional[str] = None
    items: List[KeyMetric]


ArticleBlock = Union[HeadingBlock, TextBlock, GalleryBlock, VideoBlock, QuoteBlock, StatsBlock]


class ArticleBase(BaseModel):
    slug: str = Field(..., description="Slug used as a unique identifier and URL segment")
    title: str
    subtitle: str
    location: str
    cover_url: Optional[str] = None
    video_url: Optional[str] = None
    body: Optional[str] = None
    price: Optional[str] = Field(default=None, description="Displayed price label")
    price_on_request: bool = Field(default=False, description="True if price should be hidden and shown as on-request")
    highlight: bool = False
    status: Literal["draft", "published"] = "draft"
    post_type: Literal["sale", "rent"] = "sale"
    tags: List[str] = []
    key_metrics: List[KeyMetric] = []
    gallery: List[GalleryImage] = []
    blocks: List[ArticleBlock] = []


class ArticleCreate(ArticleBase):
    """Payload used to create a new article."""


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    location: Optional[str] = None
    cover_url: Optional[str] = None
    video_url: Optional[str] = None
    body: Optional[str] = None
    price: Optional[str] = None
    price_on_request: Optional[bool] = None
    highlight: Optional[bool] = None
    status: Optional[Literal["draft", "published"]] = None
    post_type: Optional[Literal["sale", "rent"]] = None
    tags: Optional[List[str]] = None
    key_metrics: Optional[List[KeyMetric]] = None
    gallery: Optional[List[GalleryImage]] = None
    blocks: Optional[List[ArticleBlock]] = None


class ArticleResponse(ArticleBase):
    id: str
    created_at: datetime
    updated_at: datetime

