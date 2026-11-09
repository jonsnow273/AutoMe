from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.auth.router import router as auth_router
from backend.api import (
    messages_router,
    contacts_router,
    platforms_router,
    settings_router,
    analytics_router,
)
from backend.events import socket_app
import os
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from backend.connectors.session_manager import auto_start_all_bots, stop_all_bots

load_dotenv()

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-resume bots in background
    asyncio.create_task(auto_start_all_bots())
    yield
    # Cleanup on shutdown
    await stop_all_bots()

app = FastAPI(
    title="AutoMe API",
    description="AI-Powered Social Proxy System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow the React frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(platforms_router)
app.include_router(contacts_router)
app.include_router(messages_router)
app.include_router(settings_router)
app.include_router(analytics_router)

# Mount Socket.IO
app.mount("/socket.io", socket_app)


@app.get("/", tags=["Health"])
def root():
    return {"message": "AutoMe API is running", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
