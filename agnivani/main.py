"""AGNIVANI FastAPI application."""
from __future__ import annotations
import asyncio,os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,ORJSONResponse
from fastapi.staticfiles import StaticFiles
import structlog
from agnivani.api import detections,dispatch,pipeline,stream,snapshot
from agnivani.api.events import EventBroker
from agnivani.config import Settings
from agnivani.geo.registry import load_facilities
from agnivani.ingest.scheduler import process_once,scheduler_loop
from agnivani.logging_setup import configure_logging
from agnivani.models.scorer import get_scorer
from agnivani.store.duck import DuckStore

ROOT=Path(__file__).resolve().parent.parent
log=structlog.get_logger()

@asynccontextmanager
async def lifespan(app:FastAPI):
    settings=Settings(); configure_logging(settings.log_level,os.getenv("AGNIVANI_ENV")=="production")
    app.state.settings=settings; app.state.store=DuckStore(settings.data_dir); app.state.broker=EventBroker(); app.state.scorer=get_scorer(settings)
    facilities=load_facilities(settings.data_dir)
    for row in facilities.drop(columns="geometry").to_dict("records"):app.state.store.upsert_facility(row)
    app.state.store.log("STARTUP",f"AGNIVANI online; scorer={app.state.scorer.name}; offline={settings.offline_mode}")
    try:await asyncio.wait_for(process_once(app,settings.backfill_days,not settings.offline_mode),timeout=240)
    except asyncio.TimeoutError:app.state.store.log("BACKFILL","four-minute cap reached; serving partial cache",level="WARN")
    except Exception as exc:app.state.store.log("BACKFILL",f"startup ingestion unavailable: {exc}",level="WARN")
    task=asyncio.create_task(scheduler_loop(app),name="firms-poller") if not settings.offline_mode else None
    yield
    if task:
        task.cancel()
        try:await task
        except asyncio.CancelledError:pass
    app.state.broker.close(); app.state.store.close()

def create_app(settings:Settings|None=None):
    @asynccontextmanager
    async def configured_lifespan(app):
        if settings is None:
            async with lifespan(app):yield
        else:
            configure_logging(settings.log_level); app.state.settings=settings; app.state.store=DuckStore(settings.data_dir); app.state.broker=EventBroker(); app.state.scorer=get_scorer(settings)
            for row in load_facilities(settings.data_dir).drop(columns="geometry").to_dict("records"):app.state.store.upsert_facility(row)
            try:await process_once(app,settings.backfill_days,False)
            except Exception as exc:app.state.store.log("BACKFILL",f"seed unavailable: {exc}",level="WARN")
            yield; app.state.broker.close(); app.state.store.close()
    cfg = settings or Settings()
    cors_origins = cfg.cors_origins if cfg and getattr(cfg, "cors_origins", None) else [
        "http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"
    ]
    api=FastAPI(title="AGNIVANI",version="0.1.0",lifespan=configured_lifespan,default_response_class=ORJSONResponse)
    api.add_middleware(CORSMiddleware,allow_origins=cors_origins,allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
    for router in (detections.router,stream.router,dispatch.router,pipeline.router,snapshot.router):api.include_router(router,prefix="/api")
    for route,path in (("/css",ROOT/"css"),("/js",ROOT/"js")):
        if path.exists():api.mount(route,StaticFiles(directory=path),name=route.strip("/"))
    @api.get("/",include_in_schema=False)
    async def dashboard(request:Request):
        from fastapi.responses import HTMLResponse
        html = (ROOT/"index.html").read_text(encoding="utf-8")
        shim = '<script>window.AGNIVANI_API = { base: "/api", live: true };</script>'
        injected = html.replace("</body>", f"{shim}\n</body>", 1)
        return HTMLResponse(content=injected)
    @api.exception_handler(Exception)
    async def unhandled(request:Request,exc:Exception):
        log.exception("unhandled_exception",path=request.url.path,error=str(exc)); return ORJSONResponse({"error":type(exc).__name__,"detail":str(exc)},status_code=500)
    return api

app=create_app()
