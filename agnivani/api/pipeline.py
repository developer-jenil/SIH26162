"""Operator-visible pipeline log endpoint."""
from fastapi import APIRouter,Request
from .schemas import PipelineLogOut
router=APIRouter()
@router.get("/pipeline/log",response_model=list[PipelineLogOut])
def pipeline_log(request:Request):
    df=request.app.state.store.query("SELECT * FROM pipeline_log ORDER BY id DESC LIMIT 200")
    return df.astype(object).where(df.notna(), None).to_dict("records")
