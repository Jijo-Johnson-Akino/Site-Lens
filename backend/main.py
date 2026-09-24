from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.scans import router as scans_router
from backend.config import CORS_ORIGINS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="SiteLens", version="0.21.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(scans_router)


@app.exception_handler(RequestValidationError)
async def invalid_body(request: Request, _exc: RequestValidationError) -> JSONResponse:
    path = request.url.path.rstrip("/")
    if request.method == "POST" and path == "/api/scans":
        code = "INVALID_URL"
        message = "Please enter a valid website URL."
    else:
        code = "VALIDATION_ERROR"
        message = "The request could not be processed. Check the submitted values."
    return JSONResponse(
        status_code=400,
        content={"error": {"code": code, "message": message}},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
