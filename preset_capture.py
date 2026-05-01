import socket
import struct
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import config
from camera_controller import (
    GET_GIMBAL_POSITION,
    SELECT_DEVICE,
)


MIC_NAMES = ["MIC1", "MIC2", "MIC3"]
CAMERA_NAMES = ["PTZ1", "PTZ2"]
ZOOM_INFO = "/OBSBOT/WebCam/General/ZoomInfo"


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


def read_padded_string(data, offset):
    end = data.index(b"\0", offset)
    value = data[offset:end].decode("utf-8", "replace")
    offset = end + 1
    while offset % 4:
        offset += 1
    return value, offset


def parse_osc_message(data):
    address, offset = read_padded_string(data, 0)
    tags, offset = read_padded_string(data, offset)
    values = []

    for tag in tags.lstrip(","):
        if tag == "i":
            values.append(struct.unpack(">i", data[offset:offset + 4])[0])
            offset += 4
        elif tag == "f":
            values.append(struct.unpack(">f", data[offset:offset + 4])[0])
            offset += 4
        elif tag == "s":
            value, offset = read_padded_string(data, offset)
            values.append(value)
        else:
            values.append(f"<unsupported:{tag}>")

    return address, values


class OscClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.2)
        self.local_port = self.sock.getsockname()[1]

    def send(self, address, values, delay=0.1):
        self.sock.sendto(osc_message(address, values), (self.host, self.port))
        time.sleep(delay)

    def receive_for(self, seconds):
        deadline = time.monotonic() + seconds
        messages = []

        while time.monotonic() < deadline:
            try:
                data, _addr = self.sock.recvfrom(4096)
            except socket.timeout:
                continue

            try:
                messages.append(parse_osc_message(data))
            except Exception as exc:
                messages.append(("<parse-error>", [str(exc), data.hex()]))

        return messages


class PresetCapture(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CamSwitch - Capturar Preset Atual")
        self.geometry("620x460")

        self.presets = {
            "PTZ1": {mic: list(values) for mic, values in config.PTZ1.items()},
            "PTZ2": {mic: list(values) for mic, values in config.PTZ2.items()},
        }

        self.camera_var = tk.StringVar(value="PTZ1")
        self.mic_var = tk.StringVar(value="MIC1")
        self.device_var = tk.IntVar(value=config.PTZ_IDS.get("ptz1", 1))
        self.pan_var = tk.IntVar(value=0)
        self.tilt_var = tk.IntVar(value=0)
        self.zoom_var = tk.IntVar(value=2)
        self.status_var = tk.StringVar(value="Ajuste a camera no OBSBOT Center e clique em Capturar.")

        self.client = OscClient(config.CAMERA_IP, config.CAMERA_PORT)
        self._build()
        self._load_saved()

    def _build(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        top = ttk.LabelFrame(root, text="Destino do preset", padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Camera").grid(row=0, column=0, sticky="w")
        camera = ttk.Combobox(top, textvariable=self.camera_var, values=CAMERA_NAMES, width=10, state="readonly")
        camera.grid(row=1, column=0, padx=(0, 8), sticky="w")
        camera.bind("<<ComboboxSelected>>", self._on_camera_change)

        ttk.Label(top, text="Device").grid(row=0, column=1, sticky="w")
        ttk.Spinbox(top, from_=0, to=3, textvariable=self.device_var, width=6).grid(row=1, column=1, padx=(0, 8))

        ttk.Label(top, text="Microfone").grid(row=0, column=2, sticky="w")
        mic = ttk.Combobox(top, textvariable=self.mic_var, values=MIC_NAMES, width=10, state="readonly")
        mic.grid(row=1, column=2, padx=(0, 8), sticky="w")
        mic.bind("<<ComboboxSelected>>", self._load_saved)

        ttk.Button(top, text="Capturar atual", command=self._capture_async).grid(row=1, column=3, padx=(0, 8))
        ttk.Button(top, text="Salvar", command=self._save).grid(row=1, column=4)

        values = ttk.LabelFrame(root, text="Valores capturados", padding=10)
        values.pack(fill="x", pady=(10, 0))

        self._field(values, "Pan", self.pan_var, 0)
        self._field(values, "Tilt", self.tilt_var, 1)
        self._field(values, "Zoom", self.zoom_var, 2)

        ttk.Label(root, textvariable=self.status_var).pack(anchor="w", pady=(10, 4))

        self.log = tk.Text(root, height=14, width=76)
        self.log.pack(fill="both", expand=True)
        self._log(f"Escutando respostas OSC na porta local {self.client.local_port}")

    def _field(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Spinbox(parent, from_=-180, to=180, textvariable=variable, width=8).grid(row=row, column=1, sticky="w")

    def _device(self):
        return int(self.device_var.get())

    def _log(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def _on_camera_change(self, event=None):
        default_device = config.PTZ_IDS.get(self.camera_var.get().lower())
        if default_device is not None:
            self.device_var.set(default_device)
        self._load_saved()

    def _load_saved(self, event=None):
        camera = self.camera_var.get()
        mic = self.mic_var.get()
        pan, tilt, zoom = self.presets[camera][mic]
        self.pan_var.set(pan)
        self.tilt_var.set(tilt)
        self.zoom_var.set(zoom)

    def _capture_async(self):
        threading.Thread(target=self._capture, daemon=True).start()

    def _capture(self):
        self.status_var.set("Consultando OBSBOT Center...")
        self._log("")
        self._log(f"Selecionando device {self._device()}")

        self.client.send(SELECT_DEVICE, [self._device()], delay=0.2)
        self.client.send(GET_GIMBAL_POSITION, [0], delay=0.2)
        self.client.send(ZOOM_INFO, [0], delay=0.2)

        messages = self.client.receive_for(2.5)
        found_position = False
        found_zoom = False

        if not messages:
            self._log("Nenhuma resposta recebida.")

        for address, values in messages:
            self._log(f"{address} {values}")
            lower = address.lower()

            if "zoom" in lower and values:
                numeric = [v for v in values if isinstance(v, (int, float))]
                if numeric:
                    self.zoom_var.set(int(round(numeric[0])))
                    found_zoom = True

            if ("gim" in lower or "gimbal" in lower) and len(values) >= 2:
                numeric = [v for v in values if isinstance(v, (int, float))]
                if len(numeric) >= 2:
                    self.pan_var.set(int(round(numeric[0])))
                    self.tilt_var.set(int(round(numeric[1])))
                    if len(numeric) >= 3:
                        self.zoom_var.set(int(round(numeric[2])))
                    found_position = True

        if found_position:
            suffix = " e zoom" if found_zoom else ""
            self.status_var.set(f"Posicao{suffix} capturada. Clique em Salvar.")
        else:
            self.status_var.set("Nao encontrei pan/tilt na resposta. Veja o log OSC abaixo.")

    def _save(self):
        camera = self.camera_var.get()
        mic = self.mic_var.get()
        values = [int(self.pan_var.get()), int(self.tilt_var.get()), int(self.zoom_var.get())]
        self.presets[camera][mic] = values
        config.save_presets_file(self.presets)
        self.status_var.set(f"Salvo {camera}/{mic}: {values}")
        messagebox.showinfo("Preset salvo", f"{camera}/{mic} salvo em presets.json")


if __name__ == "__main__":
    PresetCapture().mainloop()
