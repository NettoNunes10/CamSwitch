import json
from pathlib import Path


SETTINGS_FILE = Path(__file__).with_name("app_settings.json")

DEFAULT_SETTINGS = {
    "CAMERA_IP": "127.0.0.1",
    "CAMERA_PORT": 16284,
    "AUTO_REPAIR_OBSBOT_OSC": True,
    "OBSBOT_OSC_METHOD": 0,
    "PTZ_IDS": {
        "ptz1": 1,
        "ptz2": 2,
    },
    "OBS_HOST": "localhost",
    "OBS_PORT": 4455,
    "OBS_PASSWORD": "",
    "OBS_EXECUTABLE": "",
    "OBSBOT_EXECUTABLE": "",
    "SCHEDULE_START": "17:50",
    "SCHEDULE_END": "19:20",
}


def load_settings():
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    if not SETTINGS_FILE.exists():
        return settings

    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[SETTINGS] Erro ao carregar app_settings.json: {exc}")
        return settings

    for key, value in saved.items():
        if isinstance(value, dict) and isinstance(settings.get(key), dict):
            settings[key].update(value)
        else:
            settings[key] = value
    return settings


def save_settings(settings):
    SETTINGS_FILE.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def apply_settings(config_globals):
    settings = load_settings()
    for key, value in settings.items():
        if key in config_globals:
            config_globals[key] = value
    return settings

