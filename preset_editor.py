import tkinter as tk
from tkinter import ttk, messagebox

import config
from camera_controller import move_to_position, nudge, select_device, send_cmd, WAKE_SLEEP


MIC_NAMES = ["MIC1", "MIC2", "MIC3"]
CAMERA_NAMES = ["PTZ1", "PTZ2"]


class PresetEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CamSwitch - Presets PTZ")
        self.resizable(False, False)

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
        self.speed_var = tk.IntVar(value=45)
        self.duration_var = tk.DoubleVar(value=0.35)
        self.step_var = tk.IntVar(value=5)
        self.status_var = tk.StringVar(value="Pronto")

        self._build()
        self._load_selected_preset()

    def _build(self):
        outer = ttk.Frame(self, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")

        setup = ttk.LabelFrame(outer, text="Camera e preset", padding=10)
        setup.grid(row=0, column=0, sticky="ew", columnspan=2)

        ttk.Label(setup, text="Camera").grid(row=0, column=0, sticky="w")
        camera = ttk.Combobox(
            setup,
            textvariable=self.camera_var,
            values=CAMERA_NAMES,
            state="readonly",
            width=10,
        )
        camera.grid(row=1, column=0, padx=(0, 8), sticky="w")
        camera.bind("<<ComboboxSelected>>", self._on_camera_change)

        ttk.Label(setup, text="Device").grid(row=0, column=1, sticky="w")
        ttk.Spinbox(setup, from_=0, to=3, textvariable=self.device_var, width=6).grid(
            row=1, column=1, padx=(0, 8), sticky="w"
        )

        ttk.Label(setup, text="Microfone").grid(row=0, column=2, sticky="w")
        mic = ttk.Combobox(
            setup,
            textvariable=self.mic_var,
            values=MIC_NAMES,
            state="readonly",
            width=10,
        )
        mic.grid(row=1, column=2, padx=(0, 8), sticky="w")
        mic.bind("<<ComboboxSelected>>", self._load_selected_preset)

        ttk.Button(setup, text="Carregar", command=self._load_selected_preset).grid(
            row=1, column=3, padx=(0, 8)
        )
        ttk.Button(setup, text="Selecionar/Wake", command=self._wake).grid(row=1, column=4)

        position = ttk.LabelFrame(outer, text="Posicao absoluta", padding=10)
        position.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self._field(position, "Pan", self.pan_var, 0)
        self._field(position, "Tilt", self.tilt_var, 1)
        self._field(position, "Zoom", self.zoom_var, 2)
        self._field(position, "Speed", self.speed_var, 3)
        self._field(position, "Step", self.step_var, 4)

        ttk.Button(position, text="Mover para valores", command=self._move_absolute).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )
        ttk.Button(position, text="Salvar preset", command=self._save_selected_preset).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )

        controls = ttk.LabelFrame(outer, text="Movimento fino", padding=10)
        controls.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(10, 0))

        ttk.Button(controls, text="Up", command=lambda: self._nudge("up")).grid(
            row=0, column=1, padx=4, pady=4
        )
        ttk.Button(controls, text="Left", command=lambda: self._nudge("left")).grid(
            row=1, column=0, padx=4, pady=4
        )
        ttk.Button(controls, text="Right", command=lambda: self._nudge("right")).grid(
            row=1, column=2, padx=4, pady=4
        )
        ttk.Button(controls, text="Down", command=lambda: self._nudge("down")).grid(
            row=2, column=1, padx=4, pady=4
        )

        ttk.Label(controls, text="Duracao").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(
            controls,
            from_=0.1,
            to=2.0,
            increment=0.05,
            textvariable=self.duration_var,
            width=8,
        ).grid(row=3, column=1, sticky="w", pady=(10, 0))

        ttk.Label(outer, textvariable=self.status_var).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )

    def _field(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Spinbox(parent, from_=-180, to=180, textvariable=variable, width=8).grid(
            row=row, column=1, sticky="w", pady=2
        )

    def _device(self):
        return int(self.device_var.get())

    def _current_values(self):
        return [
            int(self.pan_var.get()),
            int(self.tilt_var.get()),
            int(self.zoom_var.get()),
        ]

    def _on_camera_change(self, event=None):
        default_device = config.PTZ_IDS.get(self.camera_var.get().lower())
        if default_device is not None:
            self.device_var.set(default_device)
        self._load_selected_preset()

    def _load_selected_preset(self, event=None):
        camera = self.camera_var.get()
        mic = self.mic_var.get()
        pan, tilt, zoom = self.presets[camera][mic]
        self.pan_var.set(pan)
        self.tilt_var.set(tilt)
        self.zoom_var.set(zoom)
        self.status_var.set(f"{camera}/{mic} carregado: pan={pan}, tilt={tilt}, zoom={zoom}")

    def _wake(self):
        select_device(self._device())
        send_cmd(WAKE_SLEEP, [1], delay=0.3)
        self.status_var.set(f"Camera device {self._device()} selecionada e acordada")

    def _move_absolute(self):
        pan, tilt, zoom = self._current_values()
        move_to_position(
            self._device(),
            pan,
            tilt,
            zoom,
            speed=int(self.speed_var.get()),
        )
        self.status_var.set(f"Movido para pan={pan}, tilt={tilt}, zoom={zoom}")

    def _nudge(self, direction):
        nudge(
            self._device(),
            direction,
            speed=int(self.speed_var.get()),
            duration=float(self.duration_var.get()),
        )
        step = int(self.step_var.get())
        if direction == "left":
            self.pan_var.set(int(self.pan_var.get()) - step)
        elif direction == "right":
            self.pan_var.set(int(self.pan_var.get()) + step)
        elif direction == "up":
            self.tilt_var.set(int(self.tilt_var.get()) - step)
        elif direction == "down":
            self.tilt_var.set(int(self.tilt_var.get()) + step)
        self.status_var.set(f"Ajuste {direction} enviado")

    def _save_selected_preset(self):
        camera = self.camera_var.get()
        mic = self.mic_var.get()
        self.presets[camera][mic] = self._current_values()
        config.save_presets_file(self.presets)
        self.status_var.set(f"Salvo {camera}/{mic}: {self.presets[camera][mic]}")
        messagebox.showinfo("Preset salvo", f"{camera}/{mic} salvo em presets.json")


if __name__ == "__main__":
    PresetEditor().mainloop()
