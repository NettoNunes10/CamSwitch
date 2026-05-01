# ---------- Câmeras / OSC ----------
import win32con

CAMERA_IP = "127.0.0.1"
CAMERA_PORT = 16284

# Mapeamento dos dispositivos PTZ que você controla via OSC.
# Use os device indices que sua OBSBOT espera (device id) — por padrão 0 se só uma câmera,
# mas para múltiplas OBSBOTs insira os indices corretos atribuídos pelo firmware/Center.
PTZ_IDS = {
    "ptz1": 1,   # OBSBot Tiny (primeira PTZ)
    "ptz2": 2    # OBSBot Tiny (segunda PTZ)
}
# Índice usado para a câmera "fixa" (Meet) se algum comando OSC exigir índice, senão ignore.
FIXED_CAM_ID = 0

# Margens para parar os movimentos (graus)
PAN_MARGIN = 5
TILT_MARGIN = 2

# Tempo de polling / delays
AUDIO_INTERVAL = 0.1     # segundos entre leituras de áudio
SUSTAIN_TIME = 2.0       # segundos que um mic precisa ser dominante para ser considerado "falando"
SILENCE_TIMEOUT = 5.0    # se silêncio por 5s -> cena standby
MIN_LEVEL = 1e-4         # nível mínimo RMS para considerar "som" (ajuste conforme seu setup)
MOVE_POLL_DELAY = 0.05   # polling interno durante move_to_position
COOLDOWN_AFTER_SWITCH = 1.0 # espera depois do corte para evitar reentradas rápidas

# ---------- Microfones ----------
# Dicionário chave -> nome exibido (a chave será o id curto usado no programa)
# O valor é o trecho do nome do dispositivo que aparece em sounddevice.query_devices()
# Use strings parciais se quiser (comparação case-insensitive)
MIC_DEVICES = {
    "LOCUTOR": ("Livewire In 01 - LOC (AXIA IP-D", "MME"),
    "MIC2":   ("Livewire In 03 - MIC 2 (AXIA IP", "MME"),
    "MIC3":   ("Livewire In 04 - MIC 3 (AXIA IP", "MME"),
    "MIC1":   ("Livewire In 02 - MIC 1 (AXIA IP", "MME")
}

# Posições (pan, tilt, zoom) para cada mic (apenas para convidados mic2..mic4)
MIC_POSITIONS = {
    "LOCUTOR": (0, 0, 0),
    "MIC2": (-30, 5, 3),
    "MIC3": (10, 0, 3),
    "MIC1": (40, 3, 3),
}

# ---------- OBS (obs-websocket) ----------
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""  # coloque se configurou senha no obs-websocket

# Nome das cenas que existem no OBS
class OBS_SCENES:
    LOCUTOR = 'Cena Locutor'
    PTZ2 = "Cena PTZ 1" # cena com a fonte da PTZ1
    PTZ3 = "Cena PTZ 2" # cena com a fonte da PTZ2
    STANDBY = "Cena Standby"

class CAM_COMMANDS:
    MIC1 = 'alt+e'
    MIC2 = 'alt+w'
    MIC3 = 'alt+q'


PTZ1 = {
    "MIC1": [46, 1, 2],
    "MIC2": [12, 5, 4],
    "MIC3": [-43, 2, 3]
}

PTZ2 = {
    "MIC1": [53, -1, 3],
    "MIC2": [18, 2 , 4],
    "MIC3": [-34, 4, 3]
}

KEYS = {
    'alt': win32con.VK_MENU,
    'ctrl': win32con.VK_CONTROL,
    'shift': win32con.VK_SHIFT,
    'win': win32con.VK_LWIN,
    'tab': win32con.VK_TAB,
    'enter': win32con.VK_RETURN,
    'esc': win32con.VK_ESCAPE,
    'space': win32con.VK_SPACE,
    'up': win32con.VK_UP,
    'down': win32con.VK_DOWN,
    'left': win32con.VK_LEFT,
    'right': win32con.VK_RIGHT
}