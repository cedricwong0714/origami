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
    assert (
        direct["constructs"][0]["axial_span_A"] == http["constructs"][0]["axial_span_A"]
    )


def test_readings_follow_the_screw_and_do_not_call_phase_a_gap() -> None:
    body = predict_payload((3, 8, 14, 18))
    readings = {row["n_repeats"]: row for row in body["readings"]}
    constructs = {row["n_repeats"]: row for row in body["constructs"]}
    for n_repeats in (3, 8, 14):
        text = " ".join(readings[n_repeats]["reading"])
        phase = constructs[n_repeats]["end_junction"]["phase_deg"]
        assert "is a rigid screw" in text
        assert "apart" not in text
        assert f"{phase:.1f}°" in text
        assert "equal to cos of that phase" in text
    flexible = " ".join(readings[18]["reading"])
    assert "past the 15 nm project cutoff" in flexible
    assert "is a rigid screw" not in flexible
    assert "No m13 graft was named" in flexible
    grafted = " ".join(readings[8]["reading"])
    assert "repeat 3 of 8" in grafted
    assert "index 2" in grafted
    assert constructs[14]["m13_graft"]["repeat_index"] == 6
    assert readings[8]["reach"]["end_bow_A"] == (
        constructs[8]["end_junction"]["chord_A"] - constructs[8]["axial_span_A"]
    )
