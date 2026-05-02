import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from process_manager import is_process_running


PROCESS_NAMES = ("OBSBOT_Center", "OBSBOT_Main")
DEFAULT_METHOD = 0


def candidate_roots():
    home = Path.home()
    return [
        home / "AppData" / "Roaming" / "OBSBOT_Center",
        home / "AppData" / "Roaming" / "OBSBOT Center",
        home / "AppData" / "Local" / "OBSBOT_Center",
        home / "AppData" / "Local" / "OBSBOT Center",
        Path("C:/ProgramData/OBSBOT_Center"),
        Path("C:/ProgramData/OBSBOT Center"),
    ]


def find_global_ini():
    for root in candidate_roots():
        ini = root / "global.ini"
        if ini.exists():
            return ini
    return None


def read_text(path):
    for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding, errors="replace")
        except Exception:
            continue
    return ""


def backup_path(path):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.name}.bak-{stamp}")
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak-{stamp}-{index}")
        index += 1
    return candidate


def parse_ini_values(text):
    values = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def set_ini_value(lines, key, value):
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.strip().lower().startswith(prefix.lower()):
            lines[index] = f"{key}={value}"
            return
    lines.insert(0, f"{key}={value}")


def osc_config_ok(ini, host, port, method=DEFAULT_METHOD):
    text = read_text(ini)
    values = parse_ini_values(text)
    return (
        values.get("OSC", "").lower() == "true"
        and values.get("OSCConnectMethod") == str(method)
        and values.get("OSCHostIp") == host
        and values.get("OSCReceivePort") == str(port)
    )


def write_osc_config(ini, host, port, method=DEFAULT_METHOD):
    shutil.copy2(ini, backup_path(ini))
    lines = read_text(ini).splitlines()
    set_ini_value(lines, "OSC", "true")
    set_ini_value(lines, "OSCConnectMethod", str(method))
    set_ini_value(lines, "OSCHostIp", host)
    set_ini_value(lines, "OSCReceivePort", str(port))
    ini.write_text("\n".join(lines) + "\n", encoding="utf-8")


def kill_obsbot():
    command = (
        "Get-Process OBSBOT_Center,OBSBOT_Main -ErrorAction SilentlyContinue | "
        "Stop-Process -Force"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", command], check=False)


def find_obsbot_executable(custom_path=""):
    if custom_path and Path(custom_path).exists():
        return Path(custom_path)

    roots = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
    ]
    names = [
        Path("OBSBOT Center/bin/OBSBOT_Main.exe"),
        Path("OBSBOT Center/bin/OBSBOT_Center.exe"),
    ]

    for root in roots:
        for name in names:
            candidate = root / name
            if candidate.exists():
                return candidate
    return None


def start_obsbot(executable_path=""):
    executable = find_obsbot_executable(executable_path)
    if not executable:
        print("[OBSBOT] Executavel do OBSBOT Center nao encontrado.")
        return False

    creationflags = 0
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS

    subprocess.Popen(
        [str(executable)],
        cwd=str(executable.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    print(f"[OBSBOT] Iniciado: {executable}")
    return True


def ensure_obsbot_osc(
    host,
    port,
    method=DEFAULT_METHOD,
    restart=True,
    wait_after_start=5,
    executable_path="",
):
    ini = find_global_ini()
    if not ini:
        print("[OBSBOT] global.ini nao encontrado; tentando abrir OBSBOT Center.")
        started = start_obsbot(executable_path)
        if started:
            time.sleep(wait_after_start)
            ini = find_global_ini()
        if not ini:
            print("[OBSBOT] global.ini ainda nao encontrado.")
            return False

    needs_restart = False
    if osc_config_ok(ini, host, port, method):
        print(f"[OBSBOT] OSC ja esta ativo em {host}:{port}.")
    else:
        print(f"[OBSBOT] OSC desativado ou divergente em {ini}. Corrigindo...")
        write_osc_config(ini, host, port, method)
        needs_restart = True

    if not is_process_running("OBSBOT_Center", "OBSBOT_Main"):
        print("[OBSBOT] OBSBOT Center fechado. Abrindo...")
        start_obsbot(executable_path)
        time.sleep(wait_after_start)
        return True

    if restart and needs_restart:
        print("[OBSBOT] Reiniciando OBSBOT Center para aplicar OSC...")
        kill_obsbot()
        time.sleep(1.5)
        started = start_obsbot(executable_path)
        if started:
            time.sleep(wait_after_start)

    return True
