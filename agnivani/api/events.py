"""In-process fan-out for SSE events."""
import asyncio
class EventBroker:
    def __init__(self): self.queues:set[asyncio.Queue]=set(); self.closed=False
    async def subscribe(self):
        q=asyncio.Queue(maxsize=100); self.queues.add(q); return q
    def unsubscribe(self,q): self.queues.discard(q)
    async def publish(self,event,data):
        for q in list(self.queues):
            try:q.put_nowait((event,data))
            except asyncio.QueueFull:
                try:q.get_nowait(); q.put_nowait((event,data))
                except asyncio.QueueEmpty:pass
    def close(self): self.closed=True; self.queues.clear()
