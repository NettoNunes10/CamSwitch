import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from obsbot_osc_guard import ensure_obsbot_osc


KEYWORDS = ("osc", "16284", "start osc", "unknown path", "zmq", "task is busy")


def candidate_roots():
    env = {
        "APPDATA": Path.home() / "AppData" / "Roaming",
        "LOCALAPPDATA": Path.home() / "AppData" / "Local",
        "PROGRAMDATA": Path("C:/ProgramData"),
    }
    return [
        env["APPDATA"] / "OBSBOT_Center",
        env["APPDATA"] / "OBSBOT Center",
        env["LOCALAPPDATA"] / "OBSBOT_Center",
        env["LOCALAPPDATA"] / "OBSBOT Center",
        env["PROGRAMDATA"] / "OBSBOT_Center",
        env["PROGRAMDATA"] / "OBSBOT Center",
    ]


def find_existing_roots():
    return [root for root in candidate_roots() if root.exists()]


def find_interesting_files(root):
    patterns = ("*.log", "*.txt", "*.json", "*.ini", "*.conf", "*.cfg")
    files = []
    for pattern in patterns:
        files.extend(root.rglob(pattern))
    return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)


def read_text(path):
    for encoding in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding, errors="replace")
        except Exception:
            continue
    return ""


def show_status():
    roots = find_existing_roots()
    if not roots:
        print("Nenhuma pasta OBSBOT_Center encontrada nos locais comuns.")
        return

    print("Pastas encontradas:")
    for root in roots:
        print(f"- {root}")

    print("\nArquivos recentes com sinais de OSC/ZMQ:")
    found = False
    for root in roots:
        for path in find_interesting_files(root)[:80]:
            text = read_text(path)
            matches = [
                line.strip()
                for line in text.splitlines()
                if any(keyword.lower() in line.lower() for keyword in KEYWORDS)
            ]
            if not matches:
                continue
            found = True
            print(f"\n## {path}")
            for line in matches[-30:]:
                print(line)

    if not found:
        print("Nenhum trecho com OSC/ZMQ encontrado nos arquivos recentes.")


def backup_path(path):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.name}.bak-{stamp}")
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        next_candidate = path.with_name(f"{path.name}.bak-{stamp}-{index}")
        if not next_candidate.exists():
            return next_candidate
        index += 1


def backup_config_dirs(reset=False):
    roots = find_existing_roots()
    if not roots:
        print("Nenhuma pasta OBSBOT_Center encontrada para backup/reset.")
        return

    seen_targets = set()
    for root in roots:
        config_dir = root / "config"
        target = config_dir if config_dir.exists() else root
        resolved = target.resolve()
        if resolved in seen_targets:
            continue
        seen_targets.add(resolved)

        backup = backup_path(target)
        print(f"Backup: {target} -> {backup}")

        if reset:
            target.rename(backup)
        else:
            if target.is_dir():
                shutil.copytree(target, backup)
            else:
                shutil.copy2(target, backup)


def set_ini_value(lines, key, value):
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.strip().lower().startswith(prefix.lower()):
            lines[index] = f"{key}={value}"
            return
    lines.insert(0, f"{key}={value}")


def enable_osc(host, port, method):
    roots = find_existing_roots()
    if not roots:
        print("Nenhuma pasta OBSBOT_Center encontrada para configurar OSC.")
        return

    changed = False
    for root in roots:
        ini = root / "global.ini"
        if not ini.exists():
            continue

        backup = backup_path(ini)
        shutil.copy2(ini, backup)
        print(f"Backup: {ini} -> {backup}")

        text = read_text(ini)
        lines = text.splitlines()
        set_ini_value(lines, "OSC", "true")
        set_ini_value(lines, "OSCConnectMethod", str(method))
        set_ini_value(lines, "OSCHostIp", host)
        set_ini_value(lines, "OSCReceivePort", str(port))
        ini.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"OSC ativado em {ini}: host={host}, port={port}, method={method}")
        changed = True

    if not changed:
        print("Nenhum global.ini encontrado para configurar OSC.")


def kill_obsbot():
    command = (
        "Get-Process OBSBOT_Center,OBSBOT_Main -ErrorAction SilentlyContinue | "
        "Stop-Process -Force"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", command], check=False)
    print("Processos OBSBOT_Center/OBSBOT_Main finalizados se estavam abertos.")


def main():
    parser = argparse.ArgumentParser(
        description="Diagnostico e reset seguro de configuracoes do OBSBOT Center."
    )
    parser.add_argument("--status", action="store_true", help="Mostra logs/configs encontrados.")
    parser.add_argument("--backup-config", action="store_true", help="Copia configs para backup.")
    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="Renomeia a pasta config do OBSBOT Center para forcar recriacao.",
    )
    parser.add_argument("--enable-osc", action="store_true", help="Ativa OSC=true no global.ini.")
    parser.add_argument(
        "--ensure-osc",
        action="store_true",
        help="Ativa OSC se necessario e reinicia o OBSBOT Center automaticamente.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host OSC para gravar no global.ini.")
    parser.add_argument("--port", type=int, default=16284, help="Porta OSC para gravar no global.ini.")
    parser.add_argument(
        "--method",
        type=int,
        default=0,
        help="OSCConnectMethod. 0 costuma ser UDP Server.",
    )
    parser.add_argument("--kill", action="store_true", help="Fecha processos OBSBOT Center/Main.")
    args = parser.parse_args()
    requested_action = any(
        [
            args.status,
            args.backup_config,
            args.reset_config,
            args.enable_osc,
            args.ensure_osc,
            args.kill,
        ]
    )

    if args.kill:
        kill_obsbot()
    if args.backup_config:
        backup_config_dirs(reset=False)
    if args.reset_config:
        backup_config_dirs(reset=True)
    if args.enable_osc:
        enable_osc(args.host, args.port, args.method)
    if args.ensure_osc:
        ensure_obsbot_osc(args.host, args.port, method=args.method, restart=True)
    if args.status or not requested_action:
        show_status()


if __name__ == "__main__":
    main()
