"""FastAPI application: wires together middleware, routers and global error handlers.

`app` is what `fastapi dev` serves locally; `handler` wraps the same app with Mangum so it can run
on AWS Lambda (function.py calls it for every HTTP event). All endpoints live in app/routers/*.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from sqlalchemy.exc import IntegrityError

from app.routers import analytics, auth, engineers, facilities, incidents, users
from app.config import settings
from app.crud import TOTAL_COUNT_HEADER

logger = logging.getLogger(__name__)
# logs end up in CloudWatch when running on Lambda
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
    expose_headers=[TOTAL_COUNT_HEADER],  # lets the frontend read list totals for paging (local dev is cross-origin)
)

app.include_router(auth.router)
app.include_router(users.router)
# facilities.py builds one CRUD router per level of the hierarchy (facilities, buildings, floors, seats)
for router in facilities.routers:
    app.include_router(router)
app.include_router(engineers.router)
app.include_router(incidents.router)
app.include_router(analytics.router)

#A simple health check endpoint to verify that the API is running.
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Turn any unhandled database constraint violation into a 409 Conflict.

    Routers check the common cases themselves with friendlier messages; this is the safety net for
    races and anything they miss (unique names, foreign keys still referenced on delete, ...).
    The raw database error is logged but never sent to the client.
    """
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(status_code=409, content={"detail": "A database constraint was violated (e.g. a duplicate value, or the record is still in use elsewhere)."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log the full traceback and return a generic 500 so internals don't leak to clients."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error has occurred."})


# Lambda adapter. lifespan="off": the app has no startup/shutdown hooks to run.
# api_gateway_base_path strips the "/api/v1" prefix CloudFront forwards, so routes are declared without it
handler = Mangum(app, lifespan="off", api_gateway_base_path="/api/v1")