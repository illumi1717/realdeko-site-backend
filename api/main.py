from fastapi import FastAPI
from api.routers.posts_router import router
from api.routers.application_router import router as application_router
from api.routers.dekostavby_router import dekostavby_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/posts")
app.include_router(application_router, prefix="/application")
app.include_router(dekostavby_router, prefix="/dekostavby")