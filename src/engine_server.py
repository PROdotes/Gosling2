from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.engine.routers.catalog import router as catalog_router

app = FastAPI(
    title="Gosling2 Background Engine (V3CORE)",
    version="3.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog_router)
