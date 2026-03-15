"""
DriftWatch FastAPI application.
Run with: uvicorn driftwatch.api.main:app --reload --port 8000
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from driftwatch.api.routes import router

app = FastAPI(
    title="DriftWatch API",
    description=(
        "Real-time training/serving skew detector for ML pipelines. "
        "Detect feature drift, schema changes, and distribution shifts "
        "before they silently kill your model in production."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow React dashboard on localhost:3000 ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{duration}ms"
    return response


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# ── Mount routes ──────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")


# ── Root redirect to docs ─────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "DriftWatch API", "docs": "/docs", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("driftwatch.api.main:app", host="0.0.0.0", port=port, reload=True)