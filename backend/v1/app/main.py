import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from sqlalchemy.exc import IntegrityError

from app.routers import auth
from app.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = FastAPI(
    title="ACME Facility Incident Platform",
    description="Self-service facility and workplace-technology incident management for ACME employees.",
    version="0.1.0",
    #root_path=settings.root_path,  # e.g. "/prod" behind a staged API Gateway, "" locally
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # full origins incl. https://
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

#A simple health check endpoint to verify that the API is running.
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(status_code=409, content={"detail": "A database constraint was violated (e.g. a duplicate value)."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error has occurred."})


handler = Mangum(app, lifespan="off", api_gateway_base_path="/api/v1")