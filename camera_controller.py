# camera_controller.py
import socket
import struct
import time

from KeyboardCommands import send_hotkey
from config import *


SELECT_DEVICE = "/OBSBOT/WebCam/General/SelectDevice"
GET_GIMBAL_POSITION = "/OBSBOT/WebCam/General/GetGimPosInfo"
SET_GIMBAL_DEGREE = "/OBSBOT/WebCam/General/SetGimMotorDegree"
SET_GIMBAL_LEFT = "/OBSBOT/WebCam/General/SetGimbalLeft"
SET_GIMBAL_RIGHT = "/OBSBOT/WebCam/General/SetGimbalRight"
SET_GIMBAL_UP = "/OBSBOT/WebCam/General/SetGimbalUp"
SET_GIMBAL_DOWN = "/OBSBOT/WebCam/General/SetGimbalDown"
SET_ZOOM = "/OBSBOT/WebCam/General/SetZoom"
WAKE_SLEEP = "/OBSBOT/WebCam/General/WakeSleep"

DEFAULT_MOVE_SPEED = 50
COMMAND_DELAY = 0.15

_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def _osc_string(value):
    data = value.encode("utf-8") + b"\0"
    padding = (4 - len(data) % 4) % 4
    return data + (b"\0" * padding)


def _osc_int(value):
    return struct.pack(">i", int(value))


def _osc_message(address, values):
    type_tags = "," + ("i" * len(values))
    packet = _osc_string(address)
    packet += _osc_string(type_tags)
    packet += b"".join(_osc_int(value) for value in values)
    return packet


def send_cmd(address, args=0, delay=COMMAND_DELAY):
    """Envia mensagem OSC UDP no formato usado pelo OBSBOT Center."""
    values = args if isinstance(args, (list, tuple)) else [args]
    print(f"[CAM] {address} {values}")
    _sock.sendto(_osc_message(address, values), (CAMERA_IP, CAMERA_PORT))
    time.sleep(delay)


def select_device(cam):
    send_cmd(SELECT_DEVICE, [cam])


def send_win_command(command):
    print(f'comando: {command}')
    send_hotkey(command)
    time.sleep(0.5)


def wake_sleep_sequence(values):
    for cam, state in values:
        select_device(cam)
        send_cmd(WAKE_SLEEP, [state], delay=1)


def wake_up():
    wake_sleep_sequence([[0, 1], [1, 1], [2, 1], [3, 1]])


def sleep():
    wake_sleep_sequence([[0, 0], [1, 0], [2, 0], [3, 0]])


def stop_gimbal():
    send_cmd(SET_GIMBAL_LEFT, [0], delay=0.05)
    send_cmd(SET_GIMBAL_RIGHT, [0], delay=0.05)
    send_cmd(SET_GIMBAL_UP, [0], delay=0.05)
    send_cmd(SET_GIMBAL_DOWN, [0], delay=0.05)


def nudge(cam, direction, speed=45, duration=0.5):
    commands = {
        "left": SET_GIMBAL_LEFT,
        "right": SET_GIMBAL_RIGHT,
        "up": SET_GIMBAL_UP,
        "down": SET_GIMBAL_DOWN,
    }
    address = commands[direction.lower()]
    select_device(cam)
    send_cmd(WAKE_SLEEP, [1], delay=0.3)
    send_cmd(address, [speed], delay=duration)
    send_cmd(address, [0])


def get_response(address, args=0, timeout=1):
    print("[CAM] Leitura de resposta OSC nao esta configurada no cliente UDP simples.")
    send_cmd(address, args)


def get_position():
    print("[CAM] GetGimPosInfo envia a consulta, mas este cliente ainda nao escuta a resposta.")
    send_cmd(GET_GIMBAL_POSITION, [0])
    return None


def closer_cam(pan):
    print("[CAM] closer_cam depende de leitura de posicao e esta desativado.")
    return None


def move_to_position(cam, goal_pan, goal_tilt, zoom=1, speed=DEFAULT_MOVE_SPEED):
    """Move a camera selecionada para pan/tilt absolutos via OBSBOT Center OSC."""
    select_device(cam)
    send_cmd(WAKE_SLEEP, [1], delay=0.3)
    stop_gimbal()
    send_cmd(SET_GIMBAL_DEGREE, [speed, goal_pan, goal_tilt], delay=0.5)

    if zoom is not None:
        send_cmd(SET_ZOOM, [zoom])

    print(f"[{cam}] movimento enviado para ({goal_pan}, {goal_tilt}, zoom={zoom}).")
    return True


def move_to_mic(cam, mic, positions=None, speed=DEFAULT_MOVE_SPEED):
    positions = positions or MIC_POSITIONS
    pan, tilt, zoom = positions[mic]
    return move_to_position(cam, pan, tilt, zoom, speed=speed)
