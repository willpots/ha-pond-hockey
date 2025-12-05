from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

STEP_USER_DATA_SCHEMA = config_entries.FLOW_SCHEMA(
    {
        "location": {
            "selector": {
                "location": {}  # shows a map, returns latitude/longitude (and optional radius). [web:136]
            }
        },
        "freeze_threshold_f": {
            "default": 25,
            "selector": {
                "number": {
                    "min": -40,
                    "max": 40,
                    "mode": "box",
                }
            },
        },
        "required_hours": {
            "default": 72,
            "selector": {
                "number": {
                    "min": 1,
                    "max": 240,
                    "mode": "box",
                }
            },
        },
    }
)


class PondHockeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pond Hockey Alerts."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        loc = user_input["location"]
        latitude = loc["latitude"]
        longitude = loc["longitude"]

        data = {
            "latitude": latitude,
            "longitude": longitude,
            "freeze_threshold_f": user_input["freeze_threshold_f"],
            "required_hours": user_input["required_hours"],
        }

        return self.async_create_entry(
            title="Pond hockey at pond",
            data=data,
        )
