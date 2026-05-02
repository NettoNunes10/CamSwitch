import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

import pystray
from PIL import Image, ImageDraw

import config
from app_settings import load_settings, save_settings
from obsbot_osc_guard import ensure_obsbot_osc
from process_manager import ensure_obs_running


APP_DIR = Path(__file__).resolve().parent


class CamSwitchTray:
    def __init__(self):
        self.process = None
        self.icon = pystray.Icon(
            "CamSwitch",
            self._make_icon(),
            "CamSwitch",
            menu=pystray.Menu(
                pystray.MenuItem("Iniciar sistema", self.start_system),
                pystray.MenuItem("Parar sistema", self.stop_system),
                pystray.MenuItem("Configurar", self.open_settings),
                pystray.MenuItem("Abrir OBS/OBSBOT", self.ensure_apps),
                pystray.MenuItem("Sair", self.exit_app),
            ),
        )

    def _make_icon(self):
        image = Image.new("RGB", (64, 64), "#111827")
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 18, 42, 46), fill="#ef4444")
        draw.polygon([(42, 26), (56, 18), (56, 46), (42, 38)], fill="#f97316")
        draw.ellipse((18, 26, 34, 42), fill="#111827")
        return image

    def run(self):
        self.ensure_apps()
        self.icon.run()

    def ensure_apps(self, *_args):
        def worker():
            ensure_obs_running(config.OBS_EXECUTABLE)
            if config.AUTO_REPAIR_OBSBOT_OSC:
                ensure_obsbot_osc(
                    config.CAMERA_IP,
                    config.CAMERA_PORT,
                    method=config.OBSBOT_OSC_METHOD,
                    restart=True,
                    executable_path=config.OBSBOT_EXECUTABLE,
                )

        threading.Thread(target=worker, daemon=True).start()

    def start_system(self, *_args):
        if self.process and self.process.poll() is None:
            return
        self.ensure_apps()
        self.process = subprocess.Popen(
            [sys.executable, str(APP_DIR / "main.py")],
            cwd=str(APP_DIR),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )

    def stop_system(self, *_args):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process = None

    def open_settings(self, *_args):
        threading.Thread(target=SettingsWindow, daemon=True).start()

    def exit_app(self, *_args):
        self.stop_system()
        self.icon.stop()


class SettingsWindow:
    def __init__(self):
        self.settings = load_settings()
        self.root = tk.Tk()
        self.root.title("CamSwitch - Configuracao")
        self.root.resizable(False, False)
        self.vars = {}
        self._build()
        self.root.mainloop()

    def _var(self, key):
        value = self.settings.get(key, "")
        if isinstance(value, bool):
            var = tk.BooleanVar(value=value)
        else:
            var = tk.StringVar(value=str(value))
        self.vars[key] = var
        return var

    def _build(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        row = 0
        row = self._entry(frame, row, "Camera OSC host", "CAMERA_IP")
        row = self._entry(frame, row, "Camera OSC porta", "CAMERA_PORT")
        row = self._entry(frame, row, "OBS websocket host", "OBS_HOST")
        row = self._entry(frame, row, "OBS websocket porta", "OBS_PORT")
        row = self._entry(frame, row, "OBS websocket senha", "OBS_PASSWORD", show="*")
        row = self._entry(frame, row, "PTZ1 device", "PTZ_IDS.ptz1")
        row = self._entry(frame, row, "PTZ2 device", "PTZ_IDS.ptz2")
        row = self._entry(frame, row, "Inicio", "SCHEDULE_START")
        row = self._entry(frame, row, "Fim", "SCHEDULE_END")
        row = self._file_entry(frame, row, "OBS exe", "OBS_EXECUTABLE")
        row = self._file_entry(frame, row, "OBSBOT exe", "OBSBOT_EXECUTABLE")

        ttk.Checkbutton(
            frame,
            text="Reparar OSC automaticamente",
            variable=self._var("AUTO_REPAIR_OBSBOT_OSC"),
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
        row += 1

        buttons = ttk.Frame(frame)
        buttons.grid(row=row, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Salvar", command=self._save).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Fechar", command=self.root.destroy).grid(row=0, column=1)

    def _value_for_key(self, key):
        if "." not in key:
            return self.settings.get(key, "")
        first, second = key.split(".", 1)
        return self.settings.get(first, {}).get(second, "")

    def _entry(self, parent, row, label, key, show=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        var = tk.StringVar(value=str(self._value_for_key(key)))
        self.vars[key] = var
        ttk.Entry(parent, textvariable=var, width=42, show=show).grid(row=row, column=1, sticky="ew", pady=3)
        return row + 1

    def _file_entry(self, parent, row, label, key):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        var = tk.StringVar(value=str(self._value_for_key(key)))
        self.vars[key] = var
        ttk.Entry(parent, textvariable=var, width=42).grid(row=row, column=1, sticky="ew", pady=3)
        ttk.Button(parent, text="...", width=3, command=lambda: self._pick_file(var)).grid(row=row, column=2, padx=(4, 0))
        return row + 1

    def _pick_file(self, var):
        path = filedialog.askopenfilename(filetypes=[("Executaveis", "*.exe"), ("Todos", "*.*")])
        if path:
            var.set(path)

    def _save(self):
        settings = load_settings()
        for key, var in self.vars.items():
            value = var.get()
            if isinstance(var, tk.BooleanVar):
                value = bool(value)
            elif key in {"CAMERA_PORT", "OBS_PORT", "OBSBOT_OSC_METHOD"}:
                value = int(value)
            elif key.startswith("PTZ_IDS."):
                parent, child = key.split(".", 1)
                settings.setdefault(parent, {})[child] = int(value)
                continue
            settings[key] = value

        save_settings(settings)
        messagebox.showinfo("CamSwitch", "Configuracao salva. Reinicie o sistema para aplicar tudo.")


if __name__ == "__main__":
    CamSwitchTray().run()
