from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.db import run_migrations
from backend.routers import admin, auth, chat, feedback, surveys, tickets
from backend.seed import seed_accounts
from ticket_router.config import config
from ticket_router.errors import AppError


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    run_migrations()
    seed_accounts()
    yield


app = FastAPI(title="Port4 Ticket API", version="1.0.0", lifespan=lifespan)

# The React frontend (frontend/) runs as a separate process on its own port
# and calls this API over HTTP. Origins are configured via CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
    # Safety net for AppError subclasses (AIUnavailableError, etc.) raised
    # somewhere that didn't already convert them to an HTTPException - keeps
    # the API's error contract clean (never a raw stack trace) end to end.
    return JSONResponse(status_code=503, content={"detail": exc.message, "code": exc.code})


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(surveys.router)
