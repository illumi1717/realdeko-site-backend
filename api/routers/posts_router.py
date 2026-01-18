from fastapi import APIRouter
from typing import List
from dbase.collections.PostCollection import PostCollection

router = APIRouter()

@router.get("/all_posts")
def get_all_posts() -> List[dict]:
    collection = PostCollection()
    posts = collection.get_all_posts()
    return posts