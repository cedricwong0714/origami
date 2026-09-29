"""Structural analysis API is scaffold-only and keeps calibrated false."""

from __future__ import annotations

from fastapi.testclient import TestClient

from origami.api.structural import app, predict_payload


client = TestClient(app)


def test_health_is_uncalibrated() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["calibrated"] is False


def test_predict_default_constructs() -> None:
    body = client.get("/api/sa/predict").json()
    assert body["calibrated"] is False
    assert body["payloads"] is False
    assert [row["n_repeats"] for row in body["constructs"]] == [3, 8, 14]
    assert "p_clash" not in str(body["constructs"])
    assert "c_eff" not in str(body["constructs"]).lower()
    assert body["constructs"][0]["end_junction"]["delta_i"] == 2
    assert len(body["scenes"]) == 3
    assert len(body["readings"]) == 3


def test_predict_rejects_out_of_range_n() -> None:
    response = client.get("/api/sa/predict", params={"n": "2"})
    assert response.status_code == 400


def test_payload_helper_matches_http() -> None:
    direct = predict_payload((8,))
    http = client.get("/api/sa/predict", params={"n": "8"}).json()
    assert direct["constructs"][0]["axial_span_A"] == http["constructs"][0]["axial_span_A"]
