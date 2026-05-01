import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


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
    return path.with_name(f"{path.name}.bak-{stamp}")


def backup_config_dirs(reset=False):
    roots = find_existing_roots()
    if not roots:
        print("Nenhuma pasta OBSBOT_Center encontrada para backup/reset.")
        return

    for root in roots:
        config_dir = root / "config"
        target = config_dir if config_dir.exists() else root
        backup = backup_path(target)
        print(f"Backup: {target} -> {backup}")

        if reset:
            target.rename(backup)
        else:
            if target.is_dir():
                shutil.copytree(target, backup)
            else:
                shutil.copy2(target, backup)


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
    parser.add_argument("--kill", action="store_true", help="Fecha processos OBSBOT Center/Main.")
    args = parser.parse_args()

    if args.kill:
        kill_obsbot()
    if args.backup_config:
        backup_config_dirs(reset=False)
    if args.reset_config:
        backup_config_dirs(reset=True)
    if args.status or not any(vars(args).values()):
        show_status()


if __name__ == "__main__":
    main()
