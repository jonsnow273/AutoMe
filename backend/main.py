from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.auth.router import router as auth_router
import os
from dotenv import load_dotenv

load_dotenv()

# Create all DB tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AutoMe API",
    description="AI-Powered Social Proxy System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/", tags=["Health"])
def root():
    return {"message": "AutoMe API is running", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
