import argparse
import socket
import struct
import subprocess
import time

import config


CONNECTED = "/OBSBOT/WebCam/General/Connected"
SELECT_DEVICE = "/OBSBOT/WebCam/General/SelectDevice"
WAKE_SLEEP = "/OBSBOT/WebCam/General/WakeSleep"
SET_GIMBAL_LEFT = "/OBSBOT/WebCam/General/SetGimbalLeft"
SET_GIMBAL_RIGHT = "/OBSBOT/WebCam/General/SetGimbalRight"


def osc_string(value):
    data = value.encode("utf-8") + b"\0"
    padding = (4 - len(data) % 4) % 4
    return data + (b"\0" * padding)


def osc_int(value):
    return struct.pack(">i", int(value))


def osc_packet(address, values):
    tags = "," + ("i" * len(values))
    return osc_string(address) + osc_string(tags) + b"".join(osc_int(v) for v in values)


def read_string(data, offset):
    end = data.index(b"\0", offset)
    value = data[offset:end].decode("utf-8", "replace")
    offset = end + 1
    while offset % 4:
        offset += 1
    return value, offset


def parse_packet(data):
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


def print_udp_listeners(port):
    print(f"\n[1] Verificando processos UDP na porta {port}")
    command = (
        "Get-NetUDPEndpoint -LocalPort "
        f"{port} -ErrorAction SilentlyContinue | "
        "Select-Object LocalAddress,LocalPort,OwningProcess | Format-Table -AutoSize"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    print(output or "Nenhum listener UDP encontrado nessa porta.")


def candidate_hosts():
    hosts = ["127.0.0.1", socket.gethostname()]
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            host = info[4][0]
            if host not in hosts:
                hosts.append(host)
    except Exception:
        pass
    return hosts


def print_obsbot_processes():
    print("\n[1b] Procurando processos OBSBOT e portas abertas por eles")
    command = r"""
$processes = Get-Process | Where-Object { $_.ProcessName -match 'obsbot|obs' }
if (-not $processes) {
  Write-Output 'Nenhum processo com nome OBS/OBSBOT encontrado.'
  exit
}

$processes | Select-Object Id,ProcessName,Path | Format-Table -AutoSize

$ids = $processes.Id
$endpoints = Get-NetUDPEndpoint -ErrorAction SilentlyContinue |
  Where-Object { $ids -contains $_.OwningProcess } |
  Select-Object LocalAddress,LocalPort,OwningProcess

if ($endpoints) {
  Write-Output ''
  Write-Output 'UDP endpoints dos processos encontrados:'
  $endpoints | Format-Table -AutoSize
} else {
  Write-Output ''
  Write-Output 'Nenhuma porta UDP aberta pelos processos encontrados.'
}

$tcp = Get-NetTCPConnection -ErrorAction SilentlyContinue |
  Where-Object { $ids -contains $_.OwningProcess } |
  Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess

if ($tcp) {
  Write-Output ''
  Write-Output 'TCP connections/listeners dos processos encontrados:'
  $tcp | Format-Table -AutoSize
} else {
  Write-Output ''
  Write-Output 'Nenhuma porta TCP encontrada para os processos encontrados.'
}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    print(output or "Nao foi possivel consultar processos.")


def print_obsbot_files():
    print("\n[1c] Procurando configs/logs recentes do OBSBOT Center")
    command = r"""
$roots = @(
  (Join-Path $env:APPDATA 'OBSBOT Center'),
  (Join-Path $env:APPDATA 'OBSBOT_Center'),
  (Join-Path $env:LOCALAPPDATA 'OBSBOT Center'),
  (Join-Path $env:LOCALAPPDATA 'OBSBOT_Center'),
  (Join-Path $env:APPDATA 'obsbot-center'),
  (Join-Path $env:LOCALAPPDATA 'obsbot-center'),
  (Join-Path $env:PROGRAMDATA 'OBSBOT Center'),
  (Join-Path $env:PROGRAMDATA 'OBSBOT_Center')
)

foreach ($root in $roots) {
  if (Test-Path $root) {
    Write-Output ''
    Write-Output "DIR $root"
    Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match 'log|config|setting|osc|json|ini|txt|db' } |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 20 FullName,Length,LastWriteTime |
      Format-Table -AutoSize
  }
}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    print(output or "Nenhuma pasta de config/log encontrada nos locais comuns.")


def udp_diag(host, port, device, speed):
    print(f"\n[2] Teste UDP para {host}:{port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(0.35)
    print(f"Porta local do diagnostico: {sock.getsockname()[1]}")

    sequence = [
        (CONNECTED, [1], 0.4),
        (SELECT_DEVICE, [device], 0.4),
        (WAKE_SLEEP, [1], 0.5),
        (SET_GIMBAL_LEFT, [speed], 0.45),
        (SET_GIMBAL_LEFT, [0], 0.2),
        (SET_GIMBAL_RIGHT, [speed], 0.45),
        (SET_GIMBAL_RIGHT, [0], 0.2),
    ]

    for address, values, delay in sequence:
        packet = osc_packet(address, values)
        print(f"-> {address} {values} ({len(packet)} bytes)")
        try:
            sock.sendto(packet, (host, port))
        except OSError as exc:
            print(f"<- Falha ao enviar para {host}:{port}: {exc}")
            return
        deadline = time.monotonic() + delay
        while time.monotonic() < deadline:
            try:
                data, source = sock.recvfrom(4096)
            except socket.timeout:
                break
            except ConnectionResetError as exc:
                print(f"<- Windows informou porta UDP fechada ou recusada: {exc}")
                break
            try:
                parsed = parse_packet(data)
            except Exception as exc:
                parsed = ("<parse-error>", [str(exc), data.hex()])
            print(f"<- {source} {parsed[0]} {parsed[1]}")


def tcp_diag(host, port, device, speed):
    print(f"\n[3] Teste TCP para {host}:{port}")
    try:
        with socket.create_connection((host, port), timeout=2) as sock:
            print("TCP conectou. Enviando OSC sem framing extra.")
            for address, values in [
                (CONNECTED, [1]),
                (SELECT_DEVICE, [device]),
                (WAKE_SLEEP, [1]),
                (SET_GIMBAL_LEFT, [speed]),
                (SET_GIMBAL_LEFT, [0]),
            ]:
                packet = osc_packet(address, values)
                print(f"-> {address} {values} ({len(packet)} bytes)")
                sock.sendall(packet)
                time.sleep(0.3)
    except Exception as exc:
        print(f"TCP falhou: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Diagnostico OSC do OBSBOT Center.")
    parser.add_argument("--host", default=config.CAMERA_IP)
    parser.add_argument("--port", type=int, default=config.CAMERA_PORT)
    parser.add_argument("--device", type=int, default=2)
    parser.add_argument("--speed", type=int, default=35)
    parser.add_argument("--scan-hosts", action="store_true")
    parser.add_argument("--tcp", action="store_true")
    args = parser.parse_args()

    print_udp_listeners(args.port)
    print_obsbot_processes()
    print_obsbot_files()
    if args.scan_hosts:
        print("\n[2] Varrendo hosts candidatos")
        for host in candidate_hosts():
            udp_diag(host, args.port, args.device, args.speed)
    else:
        udp_diag(args.host, args.port, args.device, args.speed)
    if args.tcp:
        tcp_diag(args.host, args.port, args.device, args.speed)


if __name__ == "__main__":
    main()
