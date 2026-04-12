from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from parser import parse_task
from schemas import ParseRequest, ParseResponse

logger = logging.getLogger("task_parser_api")
if not logger.handlers:
    logging.basicConfig(
        level=os.getenv("TASK_PARSER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "TASK_PARSER_ALLOWED_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="Task Parser Assistant API",
    version="1.0.0",
    description="Parse natural-language task text into structured task metadata.",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_origin_regex=r"chrome-extension://.*",
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        )
    ],
)


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    started = time.perf_counter()
    logger.info("request.start method=%s path=%s client=%s", request.method, request.url.path, request.client)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.exception("request.error method=%s path=%s duration_ms=%.2f", request.method, request.url.path, elapsed_ms)
        raise

    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "request.complete method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/parse", response_model=ParseResponse)
def parse(request: ParseRequest) -> ParseResponse:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    logger.info("parse.request text_length=%s", len(text))
    return parse_task(text)
