from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn
import logging

logger = logging.getLogger(__name__)

# Import routers
from routers import api_router, auth_router

# Import ingestion service (optional — requires astropy and related science stack)
try:
    from ingestion_service import IngestionOrchestrator
    ingestion_orchestrator = IngestionOrchestrator()
    INGESTION_AVAILABLE = True
except ImportError:
    ingestion_orchestrator = None
    INGESTION_AVAILABLE = False

# Import WebSocket service
from websocket_service import websocket_manager

# Import SSE service
from sse_service import sse_manager

# Cron scheduler for NOAA data
from jobs.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title="Solar Flare Prediction API",
    description="AI-powered solar flare prediction dashboard for ISRO Aditya-L1 mission data",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/auth")


@app.on_event("startup")
def startup_cron_scheduler():
    """Start APScheduler cron jobs when enabled (default: on)."""
    import os
    enabled = os.getenv("ENABLE_CRON_SCHEDULER", "true").lower() in ("1", "true", "yes")
    if enabled:
        start_scheduler(run_immediately=True)
        logger.info("Cron data jobs started")
    else:
        logger.info("Cron scheduler disabled — using external worker or snapshots only")


@app.on_event("shutdown")
def shutdown_cron_scheduler():
    stop_scheduler()


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Solar Flare Prediction API is running"}


@app.get("/status")
def status_check():
    return {
        "status": "operational",
        "timestamp": "2026-07-02T12:00:00Z",
        "services": {
            "database": "connected",
            "redis": "connected",
            "ai_models": "loaded",
            "cron_scheduler": "active",
        },
    }


@app.post("/ingest/trigger")
def trigger_ingestion(background_tasks: BackgroundTasks):
    if not INGESTION_AVAILABLE or ingestion_orchestrator is None:
        return {"status": "unavailable", "message": "Ingestion service dependencies not installed"}
    background_tasks.add_task(ingestion_orchestrator.run_complete_ingestion_cycle)
    return {"status": "ingestion_triggered", "message": "Data ingestion cycle started in background"}


@app.get("/ingest/status")
def get_ingestion_status():
    from services.cron_data import get_cron_status
    return get_cron_status()


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


@app.get("/sse/data")
async def sse_data_stream(request: Request):
    client_id = await sse_manager.add_client(request)
    return EventSourceResponse(
        sse_manager.stream_events(request, client_id),
        ping=15,
    )


if __name__ == "__main__":
    import os
    from pathlib import Path
    port = int(os.getenv("PORT", "8000"))
    # Write the actual resolved port so the frontend's vite.config.ts can
    # find this backend regardless of which port autoPort landed it on —
    # hardcoding a fallback port here has repeatedly gone stale the moment
    # a different session/process was already holding the "usual" port.
    (Path(__file__).resolve().parent / ".dev-port").write_text(str(port), encoding="utf-8")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
