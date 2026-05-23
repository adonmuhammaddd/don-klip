from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import clips, files, health, jobs
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Video Clipper", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(clips.router, prefix="/api")
app.include_router(files.router, prefix="/api")
