import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.db.init_db import create_tables


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    create_tables()
    yield


app = FastAPI(title="KahveCell API", version="0.1.0", lifespan=lifespan)

configured_origins = os.getenv("KAHVECELL_CORS_ORIGINS")
allowed_origins = (
    [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    if configured_origins
    else ["http://localhost:5173", "http://127.0.0.1:5173"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(
    _request: Request, exception: HTTPException
) -> JSONResponse:
    if isinstance(exception.detail, dict):
        error = exception.detail.copy()
        data = error.pop("data", None)
    else:
        error = {"code": "HTTP_ERROR", "message": str(exception.detail)}
        data = None
    return JSONResponse(
        status_code=exception.status_code,
        content={"success": False, "data": data, "error": error},
        headers=exception.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exception: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exception.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Istek verileri gecersiz.",
                "details": details,
            },
        },
    )


@app.get("/")
def home() -> dict[str, object]:
    return {
        "success": True,
        "data": {
            "message": "KahveCell backend ayakta \u00e7al\u0131\u015f\u0131yor",
            "service": "KahveCell API",
            "version": "0.1.0",
            "docs": "/docs",
        },
        "error": None,
    }


@app.get("/health")
def health_check() -> dict[str, object]:
    return {
        "success": True,
        "data": {"status": "ok"},
        "error": None,
    }
