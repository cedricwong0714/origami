from fastapi.testclient import TestClient

from origami.api.structural import app

client = TestClient(app)
CSV = (
    "well,construct,n_repeats,batch,role,rlu\n"
    "A1,c,8,b1,blank,10\nB1,c,8,b1,sample,110\nB2,c,8,b1,sample,130\n"
)


def test_plate_endpoint_returns_rows_and_hash():
    r = client.post("/api/lab/plate", json={"csv_text": CSV, "source": "p.csv"})
    assert r.status_code == 200
    body = r.json()
    assert body["observations"][0]["y"] == 110.0
    assert len(body["input_sha256"]) == 64 and body["calibrated"] is False


def test_plate_endpoint_rejects_bad_input():
    assert client.post("/api/lab/plate", json={"csv_text": "well,rlu\nA1,1\n"}).status_code == 400
    assert client.post("/api/lab/plate", json={}).status_code == 400


def test_ablation_endpoint():
    n = 12
    body = {
        "X": [[i / n] for i in range(n)],
        "y_mech": [1 + i / n for i in range(n)],
        "y_obs": [1.5 + i / n for i in range(n)],
        "groups": [f"g{i % 3}" for i in range(n)],
    }
    r = client.post("/api/lab/ablation", json=body)
    assert r.status_code == 200 and r.json()["calibrated"] is False
    assert client.post("/api/lab/ablation", json={"X": []}).status_code == 400
