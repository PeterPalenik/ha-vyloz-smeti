"""Shared pytest fixtures for the Vyloz Smeti tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from custom_components.vyloz_smeti.const import (
    API_LOCATIONS_URL,
    API_OPTIONS_URL,
    API_SCHEDULE_URL,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .const import LOCATION_ID, MOCK_CONFIG_DATA

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Pinned "current" year used by test fixtures and dt_util.now patches.
CURRENT_YEAR = 2026
NEXT_YEAR = CURRENT_YEAR + 1


def _load_fixture(name: str) -> Any:
    """Load a JSON fixture by filename (without extension)."""
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in every test."""


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a non-added config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Bratislava",
        data=MOCK_CONFIG_DATA,
        unique_id=str(LOCATION_ID),
        version=1,
    )


@pytest.fixture
def locations_payload() -> list[dict[str, Any]]:
    """Raw locations response."""
    return _load_fixture("locations")


@pytest.fixture
def options_payload() -> dict[str, Any]:
    """Raw waste-types response."""
    return _load_fixture("options")


@pytest.fixture
def schedule_2026_payload() -> list[dict[str, Any]]:
    """Raw schedule for the current (pinned) year."""
    return _load_fixture("schedule_2026")


@pytest.fixture
def schedule_2027_payload() -> list[dict[str, Any]]:
    """Raw schedule for the next (pinned) year."""
    return _load_fixture("schedule_2027")


@pytest.fixture
def mock_api(
    aioclient_mock: AiohttpClientMocker,
    locations_payload: list[dict[str, Any]],
    options_payload: dict[str, Any],
    schedule_2026_payload: list[dict[str, Any]],
    schedule_2027_payload: list[dict[str, Any]],
) -> AiohttpClientMocker:
    """Return aiohttp mocker pre-wired with happy-path responses.

    Schedules are mocked per `year` query parameter so that the coordinator's
    two parallel fetches receive distinct payloads, allowing tests to assert
    that both years' events make it through.
    """
    aioclient_mock.get(API_LOCATIONS_URL, json=locations_payload)
    aioclient_mock.get(API_OPTIONS_URL, json=options_payload)
    aioclient_mock.get(
        f"{API_SCHEDULE_URL}?locationId={LOCATION_ID}&year={CURRENT_YEAR}",
        json=schedule_2026_payload,
    )
    aioclient_mock.get(
        f"{API_SCHEDULE_URL}?locationId={LOCATION_ID}&year={NEXT_YEAR}",
        json=schedule_2027_payload,
    )
    return aioclient_mock
