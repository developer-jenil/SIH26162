"""Safe local dispatch recording; external channels are deliberately not configured."""
from datetime import datetime,timezone
from pathlib import Path
import json,uuid
from fastapi import APIRouter,HTTPException,Request
from .schemas import DispatchRequest,DispatchOut
router=APIRouter()
@router.post("/dispatch",response_model=DispatchOut)
def dispatch(payload:DispatchRequest,request:Request):
    exists=not request.app.state.store.query("SELECT 1 FROM detections WHERE id=?",[payload.detection_id]).empty
    if not exists:raise HTTPException(404,f"Detection '{payload.detection_id}' was not found")
    now=datetime.now(timezone.utc); ident="DSP-"+uuid.uuid4().hex[:10].upper()
    status="sent" if payload.channel=="mock" else "failed"
    receipt="recorded locally; no external message sent" if status=="sent" else "external channels are disabled in the offline build"
    record={"dispatch_id":ident,"detection_id":payload.detection_id,"authority":payload.authority,"channel":payload.channel,"note":payload.note,"status":status,"receipt":receipt,"dispatched_at":now.isoformat()}
    path=Path(request.app.state.settings.data_dir)/"processed"/"dispatches.jsonl"; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(record)+"\n")
    request.app.state.store.conn.execute("INSERT INTO alerts VALUES (?,?,?)",[ident,json.dumps(record),now])
    return record
