import json
from pathlib import Path

import win32con


# ---------- Cameras / OSC ----------
CAMERA_IP = "127.0.0.1"
CAMERA_PORT = 16284
AUTO_REPAIR_OBSBOT_OSC = True
OBSBOT_OSC_METHOD = 0
PRESET_FILE = Path(__file__).with_name("presets.json")

PTZ_IDS = {
    "ptz1": 1,
    "ptz2": 2,
}
FIXED_CAM_ID = 0

PAN_MARGIN = 5
TILT_MARGIN = 2

AUDIO_INTERVAL = 0.1
SUSTAIN_TIME = 2.0
SILENCE_TIMEOUT = 5.0
MIN_LEVEL = 1e-4
MOVE_POLL_DELAY = 0.05
COOLDOWN_AFTER_SWITCH = 1.0


# ---------- Microfones ----------
MIC_DEVICES = {
    "LOCUTOR": ("Livewire In 01 - LOC (AXIA IP-D", "MME"),
    "MIC2": ("Livewire In 03 - MIC 2 (AXIA IP", "MME"),
    "MIC3": ("Livewire In 04 - MIC 3 (AXIA IP", "MME"),
    "MIC1": ("Livewire In 02 - MIC 1 (AXIA IP", "MME"),
}

MIC_POSITIONS = {
    "LOCUTOR": (0, 0, 0),
    "MIC2": (-30, 5, 3),
    "MIC3": (10, 0, 3),
    "MIC1": (40, 3, 3),
}


# ---------- OBS ----------
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""


class OBS_SCENES:
    LOCUTOR = "Cena Locutor"
    PTZ2 = "Cena PTZ 1"
    PTZ3 = "Cena PTZ 2"
    STANDBY = "Cena Standby"


class CAM_COMMANDS:
    MIC1 = "alt+e"
    MIC2 = "alt+w"
    MIC3 = "alt+q"


DEFAULT_PTZ1 = {
    "MIC1": [46, 1, 2],
    "MIC2": [12, 5, 4],
    "MIC3": [-43, 2, 3],
}

DEFAULT_PTZ2 = {
    "MIC1": [53, -1, 3],
    "MIC2": [18, 2, 4],
    "MIC3": [-34, 4, 3],
}

PTZ1 = {mic: values[:] for mic, values in DEFAULT_PTZ1.items()}
PTZ2 = {mic: values[:] for mic, values in DEFAULT_PTZ2.items()}


def load_saved_presets():
    if not PRESET_FILE.exists():
        return

    try:
        data = json.loads(PRESET_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[CONFIG] Erro ao carregar presets.json: {exc}")
        return

    if isinstance(data.get("PTZ1"), dict):
        PTZ1.update({mic: list(values) for mic, values in data["PTZ1"].items()})
    if isinstance(data.get("PTZ2"), dict):
        PTZ2.update({mic: list(values) for mic, values in data["PTZ2"].items()})


def save_presets_file(data):
    PRESET_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def camera_presets():
    return {
        "PTZ1": PTZ1,
        "PTZ2": PTZ2,
    }


load_saved_presets()


KEYS = {
    "alt": win32con.VK_MENU,
    "ctrl": win32con.VK_CONTROL,
    "shift": win32con.VK_SHIFT,
    "win": win32con.VK_LWIN,
    "tab": win32con.VK_TAB,
    "enter": win32con.VK_RETURN,
    "esc": win32con.VK_ESCAPE,
    "space": win32con.VK_SPACE,
    "up": win32con.VK_UP,
    "down": win32con.VK_DOWN,
    "left": win32con.VK_LEFT,
    "right": win32con.VK_RIGHT,
}
