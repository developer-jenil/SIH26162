from pathlib import Path
from fastapi.testclient import TestClient
from agnivani.config import Settings
from agnivani.main import create_app

def test_empty_store_api(tmp_path):
    settings=Settings(offline_mode=True,data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["ok"] is True
        assert client.get("/api/detections").json()==[]
        stats=client.get("/api/stats")
        assert stats.status_code==200 and stats.json()["total_detections"]==0
        assert client.get("/api/detections/missing").status_code==404
        assert client.get("/api/pipeline/log").status_code==200
        assert client.get("/api/facilities").status_code==200
        assert client.get("/").status_code==200

def test_seed_data_api(tmp_path):
    raw=tmp_path/"raw"/"firms";raw.mkdir(parents=True)
    source=Path(__file__).parents[1]/"firms_india.csv";(raw/"firms_india.csv").write_bytes(source.read_bytes())
    with TestClient(create_app(Settings(offline_mode=True,data_dir=tmp_path))) as client:
        result=client.get("/api/detections?hours=0&limit=5")
        assert result.status_code==200 and result.json()
        item=result.json()[0]
        assert set(["id","lat","lon","cls","conf","frp_MW","evidence"])<=set(item)
        assert len(item["evidence"])==6 and set(item["probs"])=={"FLARE","IND_FIRE","COAL","WILD","LEAK"}
        assert abs(sum(item["probs"].values())-1)<1e-4
        response=client.post("/api/dispatch",json={"detection_id":item["id"],"authority":"TEST","channel":"mock"})
        assert response.status_code==200 and response.json()["status"]=="sent"
