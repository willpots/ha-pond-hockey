import asyncio
import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

DOMAIN = "pond_hockey"

LAT = 42.3876
LON = -71.0995
FREEZE_THRESHOLD_F = 25
REQUIRED_HOURS = 72
USER_AGENT = "pond-hockey-alert/0.1 (you@example.com)"
CHECK_INTERVAL = timedelta(hours=6)

async def async_setup(hass: HomeAssistant, config: dict):
    session = aiohttp.ClientSession(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json",
        }
    )

    async def async_get_hourly_periods():
        pts_url = f"https://api.weather.gov/points/{LAT},{LON}"
        async with session.get(pts_url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        hourly_url = data["properties"]["forecastHourly"]

        async with session.get(hourly_url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        return data["properties"]["periods"]  # temps in °F for hourly forecast [web:20]

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
            longest = longest_freeze_hours(periods, FREEZE_THRESHOLD_F)

            if longest >= REQUIRED_HOURS:
                _LOGGER.info(
                    "Pond hockey READY: %s consecutive hours <= %s°F",
                    longest,
                    FREEZE_THRESHOLD_F,
                )
                hass.bus.async_fire(
                    "pond_hockey_freeze_ok",
                    {
                        "status": "ready",
                        "longest_freeze_hours": longest,
                        "threshold_f": FREEZE_THRESHOLD_F,
                        "required_hours": REQUIRED_HOURS,
                    },
                )
            else:
                _LOGGER.info(
                    "Pond hockey NOT ready: longest=%s h <= %s°F (need %s h)",
                    longest,
                    FREEZE_THRESHOLD_F,
                    REQUIRED_HOURS,
                )
                hass.bus.async_fire(
                    "pond_hockey_freeze_not_ready",
                    {
                        "status": "not_ready",
                        "longest_freeze_hours": longest,
                        "threshold_f": FREEZE_THRESHOLD_F,
                        "required_hours": REQUIRED_HOURS,
                    },
                )

        except Exception as err:
            _LOGGER.error("Error checking pond hockey conditions: %s", err)
            hass.bus.async_fire(
                "pond_hockey_error",
                {"error": str(err)},
            )

    remove_interval = async_track_time_interval(
        hass, async_check_pond_hockey, CHECK_INTERVAL
    )

    async def _close_session(event):
        remove_interval()
        await session.close()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _close_session)

    # Optionally run once at startup
    hass.async_create_task(async_check_pond_hockey())

    return True
