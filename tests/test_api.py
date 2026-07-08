"""API contract testing using TestClient."""

from __future__ import annotations

_REQUIRED_KEYS = {
    "answer",
    "path_steps",
    "amenity",
    "occupancy_level",
    "language",
    "accessibility_mode",
    "used_llm",
}


def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_guide_happy_path_returns_required_keys(client, base_payload):
    res = client.post("/api/guide", json=base_payload)
    assert res.status_code == 200
    body = res.json()
    assert _REQUIRED_KEYS.issubset(body)
    assert body["language"] == "en"
    assert isinstance(body["path_steps"], list)


def test_guide_short_circuits_without_question(client, base_payload):
    res = client.post("/api/guide", json=base_payload)
    assert res.json()["used_llm"] is False


def test_guide_offline_with_question_still_not_live(client, base_payload):
    payload = dict(base_payload, question="Where is the nearest restroom?")
    res = client.post("/api/guide", json=payload)
    assert res.status_code == 200
    assert res.json()["used_llm"] is False


def test_guide_french_language(client, base_payload):
    payload = dict(base_payload, language="fr")
    body = client.post("/api/guide", json=payload).json()
    assert body["language"] == "fr"
    assert "You are headed" not in body["answer"]
    assert "Vous vous dirigez" in body["answer"]


def test_guide_spanish_localizes_answer_and_place_names(client, base_payload):
    payload = dict(
        base_payload, language="es",
        current_location="concourse_lower_sw", accessibility_needs=["wheelchair"],
    )
    body = client.post("/api/guide", json=payload).json()
    assert body["language"] == "es"
    assert "Se dirige a" in body["answer"]
    assert body["amenity"]["name"] == "Aseo accesible noreste"
    assert any("Vestíbulo" in step["instruction"] for step in body["path_steps"])


def test_malformed_body_returns_422(client):
    res = client.post("/api/guide", json={"language": "en"})
    assert res.status_code == 422


def test_unknown_sector_via_api_returns_422(client, base_payload):
    payload = dict(base_payload, current_location="nowhere")
    res = client.post("/api/guide", json=payload)
    assert res.status_code == 422


def test_index_page_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_route_not_found_returns_404(client, base_payload, monkeypatch):
    import app.main as main_mod
    from app.services.context_engine import PathNotFoundException

    async def _raise(*args, **kwargs):
        raise PathNotFoundException("boom")

    monkeypatch.setattr(main_mod, "run_guide", _raise)
    res = client.post("/api/guide", json=base_payload)
    assert res.status_code == 404
    assert res.json()["detail"] == "boom"


def test_arena_metadata(client):
    body = client.get("/api/arena").json()
    sector_ids = {z["id"] for z in body["zones"]}
    assert {"gate_a", "concourse_lower_sw", "seating_upper"}.issubset(sector_ids)
    assert body["languages"] == ["en", "es", "fr"]
    assert "restroom" in body["intents"]
    assert body["arena"]["name"] == "SoFi Stadium"
    gate_a = next(z for z in body["zones"] if z["id"] == "gate_a")
    assert set(gate_a["name"]) == {"en", "es", "fr"}


def test_assist_alias_endpoint(client, base_payload):
    res = client.post("/api/assist", json=base_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["language"] == "en"


def test_stadium_alias_metadata(client):
    body = client.get("/api/stadium").json()
    assert body["arena"]["name"] == "SoFi Stadium"

