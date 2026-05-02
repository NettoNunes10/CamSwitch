import os
import subprocess
import time
from pathlib import Path


def is_process_running(*names):
    wanted = {name.lower() for name in names}
    command = "Get-Process | Select-Object -ExpandProperty ProcessName"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
    )
    running = {line.strip().lower() for line in result.stdout.splitlines() if line.strip()}
    return any(name.lower().removesuffix(".exe") in running for name in wanted)


def start_detached(executable, args=None, cwd=None):
    args = args or []
    executable = Path(executable)
    cwd = cwd or executable.parent
    creationflags = 0
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS

    subprocess.Popen(
        [str(executable), *args],
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def find_obs_executable(custom_path=""):
    if custom_path and Path(custom_path).exists():
        return Path(custom_path)

    roots = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
    ]
    candidates = [
        Path("obs-studio/bin/64bit/obs64.exe"),
        Path("obs-studio/bin/32bit/obs32.exe"),
    ]

    for root in roots:
        for candidate in candidates:
            path = root / candidate
            if path.exists():
                return path
    return None


def ensure_obs_running(executable_path="", wait_after_start=7):
    if is_process_running("obs64", "obs32"):
        print("[OBS] OBS ja esta aberto.")
        return True

    executable = find_obs_executable(executable_path)
    if not executable:
        print("[OBS] Executavel do OBS nao encontrado.")
        return False

    print(f"[OBS] Abrindo OBS: {executable}")
    start_detached(executable)
    time.sleep(wait_after_start)
    return True
