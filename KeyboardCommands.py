import time
import win32api
import win32con
from config import KEYS

def get_vk_code(key: str):
    key = key.lower()

    if key in KEYS:
        return KEYS[key]

    # números
    if key.isdigit():
        return ord(key)

    # letras
    if len(key) == 1:
        return ord(key.upper())

    raise ValueError(f"Tecla não suportada: {key}")

def press_key(vk):
    win32api.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)

def release_key(vk):
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)

def send_hotkey(combo: str):
    """
    Ex: "alt+3", "ctrl+shift+w", "alt+tab"
    """
    keys = combo.lower().split('+')

    vk_codes = [get_vk_code(k.strip()) for k in keys]

    # Pressiona na ordem
    for vk in vk_codes:
        press_key(vk)

    # Solta na ordem inversa
    for vk in reversed(vk_codes):
        release_key(vk)