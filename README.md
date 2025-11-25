# Custom Local Vizio Controller

Local comprehensive Vizio SmartCast TV control component for Home Assistant. Built because:
- I want to control the picture settings, e.g. brightness, contrast, backlight
- the standard media player integration became unstable

**Based on [pyvizio](https://github.com/vkorn/pyvizio)** by [vkorn](https://github.com/vkorn) - thank you for the excellent library!

## Features

### Entities Created

**Number Entities (7):**

| Entity | Range | Description |
|--------|-------|-------------|
| `number.vizio_backlight` | 0-100 | Screen backlight level |
| `number.vizio_brightness` | 0-100 | Picture brightness |
| `number.vizio_contrast` | 0-100 | Picture contrast |
| `number.vizio_color` | 0-100 | Color saturation |
| `number.vizio_tint` | 0-100 | Color tint/hue |
| `number.vizio_sharpness` | 0-100 | Picture sharpness |
| `number.vizio_volume` | 0-100 | Volume level |

> **Note:** Audio balance was removed as many Vizio TV models don't support it via the API.

**Select Entities (1):**

- `select.vizio_source`  **Unified input/app selector** - Combines physical inputs and streaming apps into one dropdown. This prevents confusion from trying to set both an input and app simultaneously (only one can be active). The list is populated by querying your TV at startup for available inputs and installed apps.

  Available options queried from my TV:
  - **Physical inputs:** CAST, HDMI-1, HDMI-2, HDMI-3, HDMI-4, HDMI-5, COMP
  - **Streaming apps:** Netflix, Hulu, Disney+, YouTube, Prime Video, Plex, AccuWeather, ...  (all apps installed on your TV)

**Switch Entities (1):**
- `switch.vizio_mute` Audio mute on/off


### Not Included (But Available on Some TVs)

These features exist in the Vizio API but aren't exposed as entities yet. Could be added if needed:

- **Picture:**
  - `auto_brightness_control` (On/Off)
- **Audio:**
  - `balance` (L/R balance - not supported on many models)
  - `tv_speakers` (Auto/On/Off)
  - `surround_sound` (On/Off)
  - `volume_leveling` (On/Off)
  - `digital_audio_out` (Auto/PCM/etc)
  - `analog_audio_out` (Variable/Fixed)
  - `lip_sync` (options/range unknown)
- **System:**
  - `power_mode` (Eco Mode/Quick Start)
  - `menu_language`
- **Timers:**
  - `sleep_timer` (Off/30min/60min/etc)
  - `auto_power_off_timer`
- **Closed Captions:**
  - `closed_captions_enabled` (On/Off)

## Installation

1. Copy `vizio_local/` folder to `/config/custom_components/vizio_local/`
2. Add to `configuration.yaml`:
   ```yaml
   vizio_local:
     host: IP_ADDRESS_OF_TV
     port: 7345
     access_token: YOUR_AUTH_TOKEN
   ```
   e.g.
   ```yaml
   vizio_local:
     host: 192.168.1.69
     port: 7345
     access_token: abcd...
   ```

3. Restart Home Assistant

## Getting Auth Token

**Important:** This component does NOT handle pairing. You must pair with your TV externally using the `pyvizio` CLI tool to get an auth token first, then add that token to `configuration.yaml`.

See [pyvizio documentation](https://github.com/vkorn/pyvizio#pairing) for full pairing details.

### Pairing Steps:

```bash
# 1. Install pyvizio CLI tool
pip3 install pyvizio

# 2. Discover your TV to get IP and port
pyvizio --ip=0 discover
# Note the IP:PORT (e.g., 192.168.1.69:7345)

# 3. Start pairing process
pyvizio --ip={ip:port} --device_type=tv pair
# This will display: Challenge type and Challenge token

# 4. ⚠️ LOOK AT YOUR TV SCREEN - A PIN CODE WILL BE DISPLAYED
# Write down the PIN code shown on your TV

# 5. Finish pairing with the PIN from your TV
pyvizio --ip={ip:port} --device_type=tv pair-finish --ch_type={challenge_type} --token={challenge_token} --pin={PIN_FROM_TV}
# Example: pyvizio --ip=192.168.1.69:7345 --device_type=tv pair-finish --ch_type=1 --token=728611 --pin=9197

# 6. Copy the Authorization token displayed
# Example output: "Authorization token: Z0r3xwykuc"

# 7. Use that auth token in configuration.yaml (see Installation above)
```

**Note:** Keep your TV powered on during pairing. The PIN expires if you wait too long.

## HTTP API Reference

### Important notes!!
1. All API calls use the auth token in the `AUTH` header. 
1. The TV uses a dynamic HASHVAL system - you must GET before PUT.

### HASHVAL System -- used for all commands

**Important:** Vizio API uses dynamic HASHVAL values that change after each modification. Always:
1. GET current value to retrieve HASHVAL
2. PUT with that HASHVAL immediately
3. HASHVAL becomes invalid after PUT

This component handles HASHVAL automatically via the coordinator.


### Power State

**Get Power State:**
```bash
curl -k "https://192.168.1.69:7345/state/device/power_mode" \
  -H "AUTH: YOUR_TOKEN"
# Returns: {"ITEMS": [{"VALUE": 1}]}  # 1=on, 0=off
```

**Power On/Off:**
```bash
# Power key press (toggles)
curl -k -X PUT "https://192.168.1.69:7345/key_command/" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"_url": "/key_command/", "KEYLIST": [{"CODESET": 11, "CODE": 1, "ACTION": "KEYPRESS"}]}'
```

### Picture Settings

**Get Setting (example: backlight):**
```bash
curl -k "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/picture/backlight" \
  -H "AUTH: YOUR_TOKEN"
# Returns: {"ITEMS": [{"HASHVAL": 3722637078, "VALUE": 30, "NAME": "Backlight"}], "HASHLIST": [...]}
```

**Set Setting (2-step process):**
```bash
# Step 1: GET to retrieve current HASHVAL (see above)
# Step 2: PUT with that HASHVAL
curl -k -X PUT "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/picture/backlight" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "_url": "/menu_native/dynamic/tv_settings/picture/backlight",
    "item_name": "SETTINGS",
    "VALUE": 50,
    "HASHVAL": 3722637078,
    "REQUEST": "MODIFY"
  }'
```

**Picture Setting Endpoints:**
- `/menu_native/dynamic/tv_settings/picture/backlight`
- `/menu_native/dynamic/tv_settings/picture/brightness`
- `/menu_native/dynamic/tv_settings/picture/contrast`
- `/menu_native/dynamic/tv_settings/picture/color`
- `/menu_native/dynamic/tv_settings/picture/tint`
- `/menu_native/dynamic/tv_settings/picture/sharpness`

### Audio Settings

**Volume:**
```bash
# Get volume
curl -k "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/audio/volume" \
  -H "AUTH: YOUR_TOKEN"

# Set volume (get HASHVAL first)
curl -k -X PUT "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/audio/volume" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "_url": "/menu_native/dynamic/tv_settings/audio/volume",
    "item_name": "SETTINGS",
    "VALUE": 20,
    "HASHVAL": 3383376686,
    "REQUEST": "MODIFY"
  }'
```

**Volume Up/Down (key commands):**
```bash
# Volume Up
curl -k -X PUT "https://192.168.1.69:7345/key_command/" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"_url": "/key_command/", "KEYLIST": [{"CODESET": 5, "CODE": 1, "ACTION": "KEYPRESS"}]}'

# Volume Down
curl -k -X PUT "https://192.168.1.69:7345/key_command/" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"_url": "/key_command/", "KEYLIST": [{"CODESET": 5, "CODE": 0, "ACTION": "KEYPRESS"}]}'
```

**Mute:**
```bash
# Get mute status
curl -k "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/audio/mute" \
  -H "AUTH: YOUR_TOKEN"
# Returns: {"ITEMS": [{"HASHVAL": 2210383572, "VALUE": "Off"}]}

# Set mute (get HASHVAL first)
curl -k -X PUT "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/audio/mute" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "_url": "/menu_native/dynamic/tv_settings/audio/mute",
    "item_name": "SETTINGS",
    "VALUE": "On",
    "HASHVAL": 2210383572,
    "REQUEST": "MODIFY"
  }'
```

**Audio Setting Endpoints:**
- `/menu_native/dynamic/tv_settings/audio/volume`
- `/menu_native/dynamic/tv_settings/audio/mute`
- `/menu_native/dynamic/tv_settings/audio/balance`
- `/menu_native/dynamic/tv_settings/audio/surround_sound`
- `/menu_native/dynamic/tv_settings/audio/volume_leveling`

### Input/Source Control

**Get Current Input:**
```bash
curl -k "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/devices/current_input" \
  -H "AUTH: YOUR_TOKEN"
# Returns: {"ITEMS": [{"HASHVAL": 2023834057, "VALUE": "HDMI-2"}]}
```

**Set Input:**
```bash
# Get HASHVAL first, then:
curl -k -X PUT "https://192.168.1.69:7345/menu_native/dynamic/tv_settings/devices/current_input" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "_url": "/menu_native/dynamic/tv_settings/devices/current_input",
    "item_name": "CURRENT_INPUT",
    "VALUE": "HDMI-2",
    "HASHVAL": 2023834057,
    "REQUEST": "MODIFY"
  }'
```

**Available Inputs:** CAST, HDMI-1, HDMI-2, HDMI-3, HDMI-4, HDMI-5, COMP

### App Control

**Launch App:**
```bash
curl -k -X PUT "https://192.168.1.69:7345/app/launch" \
  -H "AUTH: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "_url": "/app/launch",
    "VALUE": {
      "APP_ID": "1",
      "NAME_SPACE": 3,
      "MESSAGE": null
    }
  }'
```

**Popular Apps (APP_ID, NAME_SPACE):**
- Netflix: `"1", 3`
- Hulu: `"3", 3`
- Prime Video: `"2", 3`
- Disney+: `"11", 3`
- YouTube: `"9", 3`

**Note:** The `select.vizio_source` entity automatically queries your TV for the complete list of installed apps at startup and populates the dropdown with all available options. You don't need to manually specify apps - just select from the dropdown.

## Advanced Usage

**Automation Example:**
```yaml
automation:
  - alias: "Movie Mode"
    trigger:
      platform: state
      entity_id: select.vizio_source
      to: "Netflix"
    action:
      - service: number.set_value
        target:
          entity_id: number.vizio_backlight
        data:
          value: 80
      - service: number.set_value
        target:
          entity_id: number.vizio_volume
        data:
          value: 25
```

**Lovelace Card:**
```yaml
type: entities
title: Vizio TV
entities:
  - select.vizio_source
  - number.vizio_volume
  - switch.vizio_mute
  - number.vizio_backlight
  - number.vizio_brightness
  - number.vizio_contrast
```

## Configuration

**What's Configurable (in `configuration.yaml`):**
- `host` - Your TV's IP address
- `port` - TV's port (default: 7345)
- `access_token` - Auth token from pairing process

## Troubleshooting

**Entities not appearing:**
- Check logs: Settings → System → Logs, search "vizio_local"
- Verify pyvizio installed: Home Assistant will auto-install from requirements
- Confirm auth token is correct

**Settings won't change:**
- Component auto-refreshes HASHVAL before each change
- If still failing, check TV is powered on
- Wait 10 seconds for coordinator to update

**Source/app changes not working:**
- TV must be powered on
- Some apps may not be available on your model
- Check logs for specific API errors

## Credits

Built on [pyvizio](https://github.com/vkorn/pyvizio) by @vkorn

Original Vizio SmartCast API research: https://github.com/exiva/Vizio_SmartCast_API

## License

Same as pyvizio - use freely!
