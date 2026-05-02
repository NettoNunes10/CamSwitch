import argparse
import socket
import struct
import time

import config
from camera_controller import (
    SELECT_DEVICE,
    SET_GIMBAL_DEGREE,
    SET_ZOOM,
    WAKE_SLEEP,
)


DEVICE_INFO = "/OBSBOT/WebCam/General/DeviceInfo"
ZOOM_INFO = "/OBSBOT/WebCam/General/ZoomInfo"
GET_GIMBAL_POSITION = "/OBSBOT/WebCam/General/GetGimPosInfo"


def osc_string(value):
    data = value.encode("utf-8") + b"\0"
    padding = (4 - len(data) % 4) % 4
    return data + (b"\0" * padding)


def osc_int(value):
    return struct.pack(">i", int(value))


def osc_message(address, values):
    tags = "," + ("i" * len(values))
    return osc_string(address) + osc_string(tags) + b"".join(osc_int(v) for v in values)


def read_string(data, offset):
    end = data.index(b"\0", offset)
    value = data[offset:end].decode("utf-8", "replace")
    offset = end + 1
    while offset % 4:
        offset += 1
    return value, offset


def parse_osc(data):
    address, offset = read_string(data, 0)
    tags, offset = read_string(data, offset)
    values = []

    for tag in tags.lstrip(","):
        if tag == "i":
            values.append(struct.unpack(">i", data[offset:offset + 4])[0])
            offset += 4
        elif tag == "f":
            values.append(struct.unpack(">f", data[offset:offset + 4])[0])
            offset += 4
        elif tag == "s":
            value, offset = read_string(data, offset)
            values.append(value)
        else:
            values.append(f"<unsupported:{tag}>")

    return address, values


class OscProbe:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.2)
        print(f"Porta local de escuta: {self.sock.getsockname()[1]}")

    def send(self, address, values, delay=0.1):
        print(f"-> {address} {values}")
        self.sock.sendto(osc_message(address, values), (self.host, self.port))
        time.sleep(delay)

    def receive_for(self, seconds):
        deadline = time.monotonic() + seconds
        messages = []

        while time.monotonic() < deadline:
            try:
                data, source = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                address, values = parse_osc(data)
            except Exception as exc:
                address, values = "<parse-error>", [str(exc), data.hex()]
            messages.append((source, address, values))

        return messages


def extract_position(messages):
    candidates = []
    for _source, address, values in messages:
        lower = address.lower()
        numeric = [v for v in values if isinstance(v, (int, float))]

        if ("gim" in lower or "gimbal" in lower or "pos" in lower) and len(numeric) >= 2:
            candidates.append((address, numeric))

    if not candidates:
        return None

    address, numeric = candidates[-1]
    pan = int(round(numeric[0]))
    tilt = int(round(numeric[1]))
    zoom = int(round(numeric[2])) if len(numeric) >= 3 else None
    return address, [pan, tilt, zoom]


def main():
    parser = argparse.ArgumentParser(
        description="Envia preset, aguarda e compara posicao chamada vs resposta OSC."
    )
    parser.add_argument("--camera", choices=sorted(config.camera_presets().keys()), required=True)
    parser.add_argument("--mic", choices=["MIC1", "MIC2", "MIC3"], required=True)
    parser.add_argument("--host", default=config.CAMERA_IP)
    parser.add_argument("--port", type=int, default=config.CAMERA_PORT)
    parser.add_argument("--speed", type=int, default=45)
    parser.add_argument("--wait", type=float, default=5.0)
    args = parser.parse_args()

    device = config.camera_device(args.camera)
    called = list(config.camera_preset(args.camera, args.mic))
    pan, tilt, zoom = called

    print(f"Preset chamado: {args.camera}/{args.mic}")
    print(f"Device: {device}")
    print(f"Posicao chamada: pan={pan}, tilt={tilt}, zoom={zoom}")

    osc = OscProbe(args.host, args.port)
    osc.send(SELECT_DEVICE, [device], delay=0.3)
    osc.send(WAKE_SLEEP, [1], delay=0.3)
    osc.send(SET_GIMBAL_DEGREE, [args.speed, pan, tilt], delay=0.3)
    osc.send(SET_ZOOM, [zoom], delay=0.3)

    print(f"Aguardando {args.wait:.1f}s...")
    messages = osc.receive_for(args.wait)

    # Alguns layouts so respondem depois de uma nova selecao/consulta.
    osc.send(SELECT_DEVICE, [device], delay=0.2)
    osc.send(DEVICE_INFO, [0], delay=0.2)
    osc.send(GET_GIMBAL_POSITION, [0], delay=0.2)
    osc.send(ZOOM_INFO, [0], delay=0.2)
    messages.extend(osc.receive_for(2.0))

    print("\nRespostas OSC recebidas:")
    if not messages:
        print("(nenhuma)")
    for source, address, values in messages:
        print(f"<- {source} {address} {values}")

    final = extract_position(messages)
    print("\nComparacao:")
    print(f"Posicao chamada: [{pan}, {tilt}, {zoom}]")
    if final:
        address, final_values = final
        print(f"Posicao final ({address}): {final_values}")
        print(
            "Diferenca final - chamada: "
            f"[{final_values[0] - pan}, {final_values[1] - tilt}, "
            f"{None if final_values[2] is None else final_values[2] - zoom}]"
        )
    else:
        print("Posicao final: nao apareceu em resposta OSC.")


if __name__ == "__main__":
    main()
