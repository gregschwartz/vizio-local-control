# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Home Assistant custom component for local control of Vizio SmartCast TVs via the pyvizio library. Provides picture settings (backlight, brightness, contrast, etc.), audio controls (volume, mute), and unified input/app source selection.

## Architecture

- `custom_components/vizio_local/__init__.py` - Main integration setup, creates `VizioAsync` client and `DataUpdateCoordinator` that polls TV every 10 seconds
- `number.py` - Number entities for picture settings (backlight, brightness, contrast, color, tint, sharpness) and volume
- `select.py` - Unified source selector combining physical inputs and streaming apps
- `switch.py` - Mute toggle switch

All entities inherit from `CoordinatorEntity` and share the same coordinator/vizio client stored in `hass.data[DOMAIN]`.

## Key Concepts

**pyvizio library**: All TV communication goes through `VizioAsync`. The library handles HASHVAL internally - you don't need to manage it when using `set_setting()`.

**Settings API pattern**:
```python
# Get: returns Item with .value and .id (hash), or raw value
item = await vizio.get_setting("picture", "backlight")

# Set: pyvizio handles HASHVAL automatically
await vizio.set_setting("picture", "backlight", 50)
```

**Data keys in coordinator**: `picture_backlight`, `picture_brightness`, `audio_volume`, `audio_mute`, `current_source`, `power_state`

## Testing

No test suite currently. Test manually against a real TV by installing in Home Assistant:
1. Copy `custom_components/vizio_local/` to HA config
2. Add config to `configuration.yaml` with host, port, access_token
3. Restart HA and check logs with filter "vizio_local"
