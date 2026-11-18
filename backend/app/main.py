from contextlib import asynccontextmanager
import asyncio
import time
import uuid
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
import app.models  # Ensure all models are registered
from app.api.v1 import auth, profile, jobs, saved_jobs, recommendations, alerts, admin, resume_studio
from app.ingestion.scheduler import IngestionScheduler

async def periodic_scheduler_worker():
    print(f"[SCHEDULER] Periodic background worker loop started (interval: {settings.SCHEDULER_INTERVAL_SECONDS}s).", flush=True)
    while True:
        try:
            await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)
            with SessionLocal() as db:
                # Advisory lock (key: 884920) prevents concurrent execution if multiple workers/replicas are running
                lock_acquired = db.execute(text("SELECT pg_try_advisory_lock(884920)")).scalar()
                if not lock_acquired:
                    print("[SCHEDULER] Another worker/replica holds the ingestion scheduler lock. Skipping this tick.", flush=True)
                    continue
                try:
                    summary = IngestionScheduler.run_due_sources(db)
                    runs_count = len(summary.get("runs", []))
                    if runs_count > 0:
                        print(f"[SCHEDULER] Executed scheduled sync for {runs_count} due source(s): {summary}", flush=True)
                finally:
                    db.execute(text("SELECT pg_advisory_unlock(884920)"))
        except asyncio.CancelledError:
            print("[SCHEDULER] Background worker received cancellation signal. Stopping cleanly.", flush=True)
            break
        except Exception as exc:
            print(f"[SCHEDULER_ERROR] {exc}", flush=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize all tables on startup
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.", flush=True)
    scheduler_task = None
    if settings.ENABLE_BACKGROUND_SCHEDULER:
        scheduler_task = asyncio.create_task(periodic_scheduler_worker())
        print(f"Background Ingestion Scheduler activated (interval: {settings.SCHEDULER_INTERVAL_SECONDS}s).", flush=True)
    yield
    if scheduler_task:
        scheduler_task.cancel()

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-level Global Job Aggregation and Discovery Platform API (PRD v2.0)",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

from app.core.rate_limiter import auth_rate_limiter

# Rate Limiting Middleware (PRD 4.1 & 9.1)
@app.middleware("http")
async def rate_limit_auth_middleware(request: Request, call_next):
    # Preflight OPTIONS requests should never consume authentication rate limits
    if request.method == "OPTIONS":
        return await call_next(request)

    # Apply to auth mutation endpoints
    path = request.url.path
    if (path.startswith(f"{settings.API_V1_STR}/auth/login") or 
        path.startswith(f"{settings.API_V1_STR}/auth/token") or 
        path.startswith(f"{settings.API_V1_STR}/auth/register") or 
        path.startswith(f"{settings.API_V1_STR}/auth/password-reset")):
        client_ip = request.client.host if request.client else "127.0.0.1"
        if not auth_rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "detail": "Too many authentication requests. Please try again later."
                },
                headers={"Retry-After": "60"}
            )
    return await call_next(request)

# Request Correlation ID & Performance Middleware
@app.middleware("http")
async def add_correlation_and_timing_header(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    
    # Production OWASP Security Headers (PRD 9.1 & 9.4)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    
    return response

# CORS Middleware (PRD 9.1 & W3C PNA: strict explicit origins, loopback regex, private network support & credentials)
# Registered after HTTP middlewares so it executes as the outermost wrapper, ensuring all preflight OPTIONS
# requests are answered immediately without interference and all responses receive proper CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=settings.BACKEND_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)

# Global Exception Handler (PRD 8.7: consistent error format, no stack traces leaked)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    # Log internally
    print(f"[ERROR] [{correlation_id}] {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please contact support with the correlation ID.",
            "correlation_id": correlation_id
        }
    )

# Include API v1 Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(profile.router, prefix=f"{settings.API_V1_STR}/profile", tags=["Candidate Profile"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["Job Discovery"])
app.include_router(saved_jobs.router, prefix=f"{settings.API_V1_STR}/saved-jobs", tags=["Saved Jobs"])
app.include_router(recommendations.router, prefix=f"{settings.API_V1_STR}/recommendations", tags=["Recommendations"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["Job Alerts"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Administration"])
app.include_router(resume_studio.router, prefix=f"{settings.API_V1_STR}/resume-studio", tags=["Resume Studio"])

@app.get("/")
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "version": "2.0.0",
        "status": "ONLINE",
        "documentation": "/api/docs"
    }

@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "HEALTHY", "database": "CONNECTED", "version": "2.0.0"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "DEGRADED", "database": "DISCONNECTED", "error": str(e)}
        )
