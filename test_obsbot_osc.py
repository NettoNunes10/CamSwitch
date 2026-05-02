import argparse
import socket
import struct
import time

import config


SET_GIMBAL_DEGREE = "/OBSBOT/WebCam/General/SetGimMotorDegree"
CONNECTED = "/OBSBOT/WebCam/General/Connected"
SELECT_DEVICE = "/OBSBOT/WebCam/General/SelectDevice"
GET_GIMBAL_POSITION = "/OBSBOT/WebCam/General/GetGimPosInfo"
SET_GIMBAL_LEFT = "/OBSBOT/WebCam/General/SetGimbalLeft"
SET_GIMBAL_RIGHT = "/OBSBOT/WebCam/General/SetGimbalRight"
SET_GIMBAL_UP = "/OBSBOT/WebCam/General/SetGimbalUp"
SET_GIMBAL_DOWN = "/OBSBOT/WebCam/General/SetGimbalDown"
SET_ZOOM = "/OBSBOT/WebCam/General/SetZoom"
WAKE_SLEEP = "/OBSBOT/WebCam/General/WakeSleep"


def osc_string(value):
    data = value.encode("utf-8") + b"\0"
    padding = (4 - len(data) % 4) % 4
    return data + (b"\0" * padding)


def osc_int(value):
    return struct.pack(">i", int(value))


def osc_message(address, values):
    type_tags = "," + ("i" * len(values))
    packet = osc_string(address)
    packet += osc_string(type_tags)
    packet += b"".join(osc_int(value) for value in values)
    return packet


def send_udp(sock, ip, port, address, values, delay=0.35):
    print(f"UDP {ip}:{port} {address} {values}")
    sock.sendto(osc_message(address, values), (ip, port))
    time.sleep(delay)


def test_nudge(sock, ip, port, device, speed):
    send_udp(sock, ip, port, SELECT_DEVICE, [device], delay=0.4)
    send_udp(sock, ip, port, WAKE_SLEEP, [1], delay=0.7)
    send_udp(sock, ip, port, SET_GIMBAL_LEFT, [speed], delay=0.5)
    send_udp(sock, ip, port, SET_GIMBAL_LEFT, [0], delay=0.2)
    send_udp(sock, ip, port, SET_GIMBAL_RIGHT, [speed], delay=0.5)
    send_udp(sock, ip, port, SET_GIMBAL_RIGHT, [0], delay=0.2)


def stop_all(sock, ip, port, device):
    send_udp(sock, ip, port, SELECT_DEVICE, [device], delay=0.25)
    for address in [SET_GIMBAL_LEFT, SET_GIMBAL_RIGHT, SET_GIMBAL_UP, SET_GIMBAL_DOWN]:
        send_udp(sock, ip, port, address, [0], delay=0.1)


def recover(sock, ip, port, device, speed):
    send_udp(sock, ip, port, CONNECTED, [1], delay=0.25)
    send_udp(sock, ip, port, SELECT_DEVICE, [device], delay=0.4)
    send_udp(sock, ip, port, WAKE_SLEEP, [0], delay=0.8)
    send_udp(sock, ip, port, WAKE_SLEEP, [1], delay=0.8)
    stop_all(sock, ip, port, device)
    test_nudge(sock, ip, port, device, speed)


def send_absolute_position(sock, ip, port, device, pan, tilt, zoom, speed):
    send_udp(sock, ip, port, SELECT_DEVICE, [device], delay=0.3)
    send_udp(sock, ip, port, WAKE_SLEEP, [1], delay=0.3)
    send_udp(sock, ip, port, SET_GIMBAL_DEGREE, [speed, pan, tilt], delay=0.5)
    if zoom is not None:
        send_udp(sock, ip, port, SET_ZOOM, [zoom])


def camera_name_from_device(device):
    for key, value in config.PTZ_IDS.items():
        if value == device:
            return key.upper()
    return None


def transform_position(pan, tilt, transform):
    transforms = {
        "normal": (pan, tilt),
        "invert-pan": (-pan, tilt),
        "invert-tilt": (pan, -tilt),
        "invert-both": (-pan, -tilt),
        "swap": (tilt, pan),
        "swap-invert-pan": (-tilt, pan),
        "swap-invert-tilt": (tilt, -pan),
        "swap-invert-both": (-tilt, -pan),
    }
    return transforms[transform]


TRANSFORMS = [
    "normal",
    "invert-pan",
    "invert-tilt",
    "invert-both",
    "swap",
    "swap-invert-pan",
    "swap-invert-tilt",
    "swap-invert-both",
]


def main():
    parser = argparse.ArgumentParser(
        description="Teste direto de comandos OSC UDP no OBSBOT Center."
    )
    parser.add_argument("--ip", default=config.CAMERA_IP)
    parser.add_argument("--port", type=int, default=config.CAMERA_PORT)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--speed", type=int, default=45)
    parser.add_argument("--pan", type=int, default=20)
    parser.add_argument("--tilt", type=int, default=0)
    parser.add_argument("--zoom", type=int)
    parser.add_argument(
        "--transform",
        choices=TRANSFORMS,
        default="normal",
        help="Transforma pan/tilt antes de enviar para testar convencao de eixos.",
    )
    parser.add_argument(
        "--try-transforms",
        action="store_true",
        help="Testa todas as variacoes comuns de pan/tilt com pausa entre elas.",
    )
    parser.add_argument("--wake", action="store_true")
    parser.add_argument("--sleep", action="store_true")
    parser.add_argument("--nudge", action="store_true")
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--get-pos", action="store_true")
    parser.add_argument(
        "--controller",
        action="store_true",
        help="Usa camera_controller.move_to_position em vez do envio local do teste.",
    )
    parser.add_argument(
        "--direct-degree",
        action="store_true",
        help="Testa SetGimMotorDegree com [device, speed, pan, tilt].",
    )
    parser.add_argument(
        "--preset",
        choices=["LOCUTOR", "MIC1", "MIC2", "MIC3"],
        help="Preset por microfone. Para MIC1-3, usa presets.json quando conseguir identificar a PTZ pelo device.",
    )
    parser.add_argument(
        "--camera",
        choices=sorted(config.camera_presets().keys()),
        help="Usa presets por camera vindos de presets.json, ex: PTZ1.",
    )
    parser.add_argument(
        "--mic",
        choices=["MIC1", "MIC2", "MIC3"],
        help="Microfone do preset salvo em presets.json.",
    )
    args = parser.parse_args()

    pan = args.pan
    tilt = args.tilt
    zoom = args.zoom

    if args.camera or args.mic:
        if not args.camera or not args.mic:
            parser.error("--camera e --mic precisam ser usados juntos.")
        args.device = config.camera_device(args.camera)
        pan, tilt, preset_zoom = config.camera_preset(args.camera, args.mic)
        if zoom is None:
            zoom = preset_zoom
        print(
            f"Preset JSON: {args.camera}/{args.mic} -> "
            f"device={args.device}, pan={pan}, tilt={tilt}, zoom={zoom}"
        )

    if args.preset:
        camera_name = camera_name_from_device(args.device)
        if args.preset != "LOCUTOR" and camera_name:
            pan, tilt, preset_zoom = config.camera_preset(camera_name, args.preset)
            if zoom is None:
                zoom = preset_zoom
            print(
                f"Preset JSON: {camera_name}/{args.preset} -> "
                f"device={args.device}, pan={pan}, tilt={tilt}, zoom={zoom}"
            )
        else:
            pan, tilt, preset_zoom = config.MIC_POSITIONS[args.preset]
            if zoom is None:
                zoom = preset_zoom
            print(
                f"Preset legacy MIC_POSITIONS: {args.preset} -> "
                f"device={args.device}, pan={pan}, tilt={tilt}, zoom={zoom}"
            )

    if args.controller:
        from camera_controller import move_to_position

        if args.try_transforms:
            original_pan, original_tilt = pan, tilt
            for transform in TRANSFORMS:
                test_pan, test_tilt = transform_position(original_pan, original_tilt, transform)
                print(
                    f"\nTransform {transform}: "
                    f"pan={test_pan}, tilt={test_tilt}, zoom={zoom}"
                )
                move_to_position(args.device, test_pan, test_tilt, zoom, speed=args.speed)
                input("Confira a camera e pressione Enter para testar o proximo...")
            return

        pan, tilt = transform_position(pan, tilt, args.transform)
        if args.transform != "normal":
            print(f"Transform aplicado: {args.transform} -> pan={pan}, tilt={tilt}")

        try:
            move_to_position(args.device, pan, tilt, zoom, speed=args.speed)
        except TypeError as exc:
            if "speed" not in str(exc):
                raise
            move_to_position(args.device, pan, tilt, zoom)
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if args.sweep:
        for port in [args.port, 16284, 16283, 16282, 9000]:
            for device in [0, 1, 2, 3]:
                print(f"\n=== Testando port={port} device={device} ===")
                test_nudge(sock, args.ip, port, device, args.speed)
        print("\nSweep concluido. Se nada moveu, o OBSBOT Center provavelmente nao esta ouvindo UDP OSC.")
        return

    if args.wake:
        send_udp(sock, args.ip, args.port, SELECT_DEVICE, [args.device], delay=0.4)
        send_udp(sock, args.ip, args.port, WAKE_SLEEP, [1], delay=1)

    if args.sleep:
        send_udp(sock, args.ip, args.port, SELECT_DEVICE, [args.device], delay=0.4)
        send_udp(sock, args.ip, args.port, WAKE_SLEEP, [0], delay=1)
        return

    if args.get_pos:
        send_udp(sock, args.ip, args.port, SELECT_DEVICE, [args.device], delay=0.4)
        send_udp(sock, args.ip, args.port, GET_GIMBAL_POSITION, [0])
        return

    if args.nudge:
        test_nudge(sock, args.ip, args.port, args.device, args.speed)
        return

    if args.recover:
        recover(sock, args.ip, args.port, args.device, args.speed)
        return

    if args.direct_degree:
        send_udp(sock, args.ip, args.port, SET_GIMBAL_DEGREE, [args.device, args.speed, pan, tilt])
    else:
        send_absolute_position(sock, args.ip, args.port, args.device, pan, tilt, zoom, args.speed)

    print("Comando enviado. Se nao moveu, rode com --nudge e depois --sweep.")


if __name__ == "__main__":
    main()
