"""Vizio Local Control integration."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from pyvizio import VizioAsync

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import discovery

_LOGGER = logging.getLogger(__name__)

DOMAIN = "vizio_local"
PLATFORMS = [Platform.NUMBER, Platform.SELECT, Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from configuration.yaml."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    host = conf.get("host")
    port = conf.get("port", 7345)
    token = conf.get("access_token")

    if not host or not token:
        _LOGGER.error("Missing required configuration: host and access_token")
        return False

    # Create Vizio client
    vizio = VizioAsync("0.0.0.0", f"{host}:{port}", "Vizio Greg", token, "tv")

    # Last good values, merged into every update so entities hold state
    # instead of going unknown while the TV is in standby. In Eco Mode the
    # SmartCast API stays reachable but returns empty payloads for everything.
    last_good: dict = {}
    was_asleep: bool | None = None
    boost_until = 0.0

    async def _poll():
        """Fetch data from Vizio."""
        nonlocal was_asleep
        data = {}

        try:
            power_state = await vizio.get_power_state(log_api_exception=False)
        except Exception as e:
            _LOGGER.debug(f"Failed to get power state: {e}")
            power_state = None

        if was_asleep and power_state is not True:
            # TV still in standby: don't hammer the dead API with the full
            # settings sweep; one power probe per cycle detects wake-up.
            return {**last_good, "power_state": False}

        # get_setting returns int/str directly (not Item objects)
        for setting in ["backlight", "brightness", "contrast", "color", "tint", "sharpness"]:
            try:
                val = await vizio.get_setting("picture", setting, log_api_exception=False)
                if val is not None:
                    data[f"picture_{setting}"] = val
                    _LOGGER.debug(f"Got picture {setting}: {val}")
            except Exception as e:
                _LOGGER.debug(f"Failed to get picture {setting}: {e}")

        for setting in ["volume", "mute"]:
            try:
                val = await vizio.get_setting("audio", setting, log_api_exception=False)
                if val is not None:
                    data[f"audio_{setting}"] = val
                    _LOGGER.debug(f"Got audio {setting}: {val}")
                else:
                    _LOGGER.debug(f"No data returned for audio {setting}")
            except Exception as e:
                _LOGGER.debug(f"Failed to get audio {setting}: {e}")

        got_settings = any(k.startswith(("picture_", "audio_")) for k in data)
        # Standby: power query empty/false AND no settings responded.
        # Report off, never unknown, so downstream guards keep working.
        asleep = power_state is not True and not got_settings
        data["power_state"] = power_state is True or power_state == 1

        if data["power_state"]:
            # Get current input/app (only meaningful while the TV is on;
            # while asleep we hold the last known source instead)
            try:
                current_input = await vizio.get_current_input(log_api_exception=False)
                _LOGGER.debug(f"Raw get_current_input returned: {current_input!r}")

                # If on SmartCast input (or input is None while TV is on), try to get app
                if not current_input or (current_input and current_input.upper() == "SMARTCAST"):
                    current_app = await vizio.get_current_app(log_api_exception=False)
                    _LOGGER.debug(f"Raw get_current_app returned: {current_app!r}")
                    if current_app and current_app != "_UNKNOWN_APP":
                        data["current_source"] = current_app
                    elif current_input:
                        data["current_source"] = current_input
                    else:
                        data["current_source"] = "SmartCast"
                else:
                    data["current_source"] = current_input
                    _LOGGER.debug(f"Current source: {current_input} (input)")
            except Exception as e:
                _LOGGER.debug(f"Failed to get current input/app: {e}")

        # Get power mode (Eco Mode vs Quick Start) - needed for power switch
        try:
            val = await vizio.get_setting("system", "power_mode", log_api_exception=False)
            if val is not None:
                data["power_mode"] = val
                _LOGGER.debug(f"Power mode: {val}")
        except Exception as e:
            _LOGGER.debug(f"Failed to get power mode: {e}")

        if asleep != was_asleep:
            _LOGGER.info(
                "TV is %s (power_state=%r, settings responded: %s)",
                "asleep/standby" if asleep else "awake",
                power_state,
                got_settings,
            )
            was_asleep = asleep

        merged = {**last_good, **data}
        last_good.clear()
        last_good.update(merged)
        _LOGGER.debug(f"Coordinator update complete. Data keys: {list(merged.keys())}")
        return merged

    async def async_update_data():
        """Poll, then pick the next poll interval adaptively."""
        merged = await _poll()
        if time.monotonic() < boost_until:
            # Burst mode after an IR power command (vizio_local.boost_polling)
            coordinator.update_interval = timedelta(seconds=1)
        elif merged.get("power_state"):
            coordinator.update_interval = timedelta(seconds=10)
        else:
            # While off it's a single cheap power probe, so poll fast to
            # catch turn-on almost immediately
            coordinator.update_interval = timedelta(seconds=2)
        return merged

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="vizio_local",
        update_method=async_update_data,
        update_interval=timedelta(seconds=10),
    )

    await coordinator.async_refresh()

    async def handle_boost_polling(call) -> None:
        """Poll every 1s for the next N seconds (call right after an IR power command)."""
        nonlocal boost_until
        duration = call.data.get("duration", 30)
        boost_until = time.monotonic() + duration
        _LOGGER.info(f"Boost polling: 1s interval for {duration}s")
        coordinator.update_interval = timedelta(seconds=1)
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "boost_polling", handle_boost_polling)

    hass.data[DOMAIN] = {
        "coordinator": coordinator,
        "vizio": vizio,
    }

    # Load platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True
