import os
from fastapi import FastAPI
from api.routers.posts_router import router
from api.routers.application_router import router as application_router
from api.routers.dekostavby_router import dekostavby_router
from api.routers.articles_router import articles_router
from api.routers.media_router import media_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(application_router)
app.include_router(dekostavby_router, prefix="/dekostavby")
app.include_router(articles_router)
app.include_router(media_router)

media_directory = os.getenv("MEDIA_ROOT", "media")
if not os.path.isdir(media_directory):
    os.makedirs(media_directory, exist_ok=True)

app.mount("/media", StaticFiles(directory=media_directory), name="media")