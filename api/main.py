from fastapi import FastAPI
from api.routers.posts_router import router

app = FastAPI()

app.include_router(router)