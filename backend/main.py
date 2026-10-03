import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config import settings
from database import init_db, engine, ping
from logging_config import configure_logging, get_logger
from routers import entries as entries_router
from routers import foods as foods_router

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("Started %s in %s mode", settings.app_name, settings.app_env)
    yield
    engine.dispose()
    log.info("Shut down cleanly")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    log.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(IntegrityError)
async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    log.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    reason = str(exc.orig).upper()
    if "UNIQUE" in reason:
        detail = "A record with that name already exists."
    elif "FOREIGN KEY" in reason:
        detail = "Referenced record does not exist or is still in use."
    else:
        detail = "That record conflicts with an existing one."
    return JSONResponse(status_code=409, content={"detail": detail})


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    log.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Please retry."})


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server."})


@app.get("/health", tags=["system"])
def health() -> dict:
    database_ok = ping()
    return {"status": "ok" if database_ok else "degraded", "database": database_ok}


app.include_router(foods_router.router)
app.include_router(entries_router.router)