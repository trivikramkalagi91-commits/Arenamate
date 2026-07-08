"""Shared pytest configuration and fixtures for ArenaMate."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _settings(**overrides) -> Settings:
    params = {
        "gemini_api_key": None,  # Force mock client offline by default
        "rate_limit_capacity": 1000,
        "rate_limit_refill_per_sec": 1000.0,
        "allowed_origins": ["http://testserver"],
    }
    params.update(overrides)
    return Settings(**params)


@pytest.fixture
def settings() -> Settings:
    return _settings()


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def make_client() -> Callable[..., TestClient]:
    """Build custom TestClient with customized overrides."""

    def _make(**overrides) -> TestClient:
        return TestClient(create_app(_settings(**overrides)))

    return _make


@pytest.fixture
def base_payload() -> dict:
    """Standard context payload."""
    return {
        "language": "en",
        "current_location": "concourse_lower_sw",
        "destination_intent": "restroom",
        "accessibility_needs": ["none"],
        "minutes_to_kickoff": 20,
    }
