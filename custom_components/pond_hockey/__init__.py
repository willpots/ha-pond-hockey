from datetime import timedelta
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CHECK_INTERVAL = timedelta(hours=6)
USER_AGENT = "pond-hockey-alert/0.1 (you@example.com)"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via YAML (unused when using config entries)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pond Hockey from a config entry."""
    latitude: float = entry.data["latitude"]
    longitude: float = entry.data["longitude"]
    freeze_threshold_f: float = entry.data["freeze_threshold_f"]
    required_hours: int = entry.data["required_hours"]

    session = aiohttp.ClientSession(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
        }
    )

    async def async_get_hourly_periods():
        pts_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        async with session.get(pts_url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        hourly_url = data["properties"]["forecastHourly"]

        async with session.get(hourly_url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return data["properties"]["periods"]  # temps in °F for hourly forecast. [web:20]

    def longest_freeze_hours(periods, threshold_f):
        longest = 0
        current = 0
        for p in periods:
            temp_f = p["temperature"]
            if temp_f <= threshold_f:
                current += 1
                if current > longest:
                    longest = current
            else:
                current = 0
        return longest

    async def async_check_pond_hockey(now=None):
        try:
            periods = await async_get_hourly_periods()
            longest = longest_freeze_hours(periods, freeze_threshold_f)

            event_data = {
                "latitude": latitude,
                "longitude": longitude,
                "longest_freeze_hours": longest,
                "threshold_f": freeze_threshold_f,
                "required_hours": required_hours,
            }

            if longest >= required_hours:
                hass.bus.async_fire("pond_hockey_freeze_ok", event_data)
            else:
                hass.bus.async_fire("pond_hockey_freeze_not_ready", event_data)

        except Exception as err:
            _LOGGER.error("Error checking pond hockey conditions: %s", err)
            hass.bus.async_fire("pond_hockey_error", {"error": str(err)})

    remove_interval = async_track_time_interval(
        hass, async_check_pond_hockey, CHECK_INTERVAL
    )

    async def _close_session(event):
        remove_interval()
        await session.close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _close_session)
    hass.async_create_task(async_check_pond_hockey())

    return True
