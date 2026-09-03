"""Server-Sent Event stream with a mandatory heartbeat."""
import asyncio, json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
router=APIRouter()
@router.get("/stream")
async def stream(request:Request):
    async def events():
        q=await request.app.state.broker.subscribe()
        try:
            while not await request.is_disconnected():
                try:
                    event,data=await asyncio.wait_for(q.get(),timeout=15)
                    yield {"event":event,"data":json.dumps(data,default=str)}
                except asyncio.TimeoutError:
                    yield {"event":"heartbeat","data":json.dumps({"ok":True})}
        finally:request.app.state.broker.unsubscribe(q)
    return EventSourceResponse(events(),ping=None)
