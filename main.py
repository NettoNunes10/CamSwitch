import time
import threading
from queue import Queue, Empty
from datetime import datetime, time as dtime, timedelta

import config
from mic_monitor import MicMonitor
from camera_controller import move_to_position, send_win_command, wake_up, sleep
from obs_control import OBSController


# ==============================
# CONFIGURACAO DE HORARIO
# ==============================
INICIO = dtime(17, 50)  # 18:00
FIM = dtime(19, 20)     # 19:00

LOCUTOR_CONFIRM_TIME = 0.5
GUEST_CONFIRM_TIME = 1.0
POST_SWITCH_COOLDOWN = 2.0


# ==============================
# ESTADO DO SISTEMA
# ==============================
obs = None
ptz2_cam = None
ptz3_cam = None
current_mic = None
current_scene = config.OBS_SCENES.LOCUTOR


def dentro_do_horario():
    agora = datetime.now().time()
    if INICIO <= FIM:
        return INICIO <= agora <= FIM
    return agora >= INICIO or agora <= FIM


def segundos_ate_inicio():
    agora = datetime.now()
    inicio = agora.replace(
        hour=INICIO.hour,
        minute=INICIO.minute,
        second=0,
        microsecond=0,
    )

    if agora > inicio:
        inicio = inicio + timedelta(days=1)

    return (inicio - agora).total_seconds()


def reset_runtime_state():
    global current_mic, ptz2_cam, ptz3_cam
    current_mic = None
    ptz2_cam = None
    ptz3_cam = None


# ==============================
# FILAS DE COMUNICACAO
# ==============================
audio_to_control = Queue()
control_to_camera = Queue()
camera_to_control = Queue()
NO_AUDIO_EVENT = object()


def set_scene(scene_name):
    global current_scene
    current_scene = scene_name
    if obs:
        obs.set_scene(scene_name)


def audio_callback(data):
    audio_to_control.put(data)


def get_latest_mic(timeout=0.1):
    """Retorna a amostra mais recente, descartando eventos antigos da fila."""
    try:
        latest = audio_to_control.get(timeout=timeout)
    except Empty:
        return NO_AUDIO_EVENT

    while True:
        try:
            latest = audio_to_control.get_nowait()
        except Empty:
            return latest


def mic_is_stable(expected_mic, duration):
    """Confirma o microfone dominante usando novas leituras do monitor."""
    deadline = time.monotonic() + duration
    last_seen = expected_mic

    while time.monotonic() < deadline:
        sample = get_latest_mic(timeout=0.1)
        if sample is NO_AUDIO_EVENT:
            continue
        if sample is None:
            return False

        last_seen = sample
        if last_seen != expected_mic:
            return False

    return last_seen == expected_mic


def switch_to_locutor():
    global current_mic
    set_scene(config.OBS_SCENES.LOCUTOR)
    current_mic = 'LOCUTOR'
    time.sleep(POST_SWITCH_COOLDOWN)


def switch_to_guest(top_mic):
    global current_mic, ptz2_cam, ptz3_cam

    if current_scene != config.OBS_SCENES.PTZ2:
        send_win_command('alt+2')
        target_scene = config.OBS_SCENES.PTZ2
    else:
        send_win_command('alt+3')
        target_scene = config.OBS_SCENES.PTZ3

    command = getattr(config.CAM_COMMANDS, top_mic, None)
    if command and ptz2_cam != top_mic and ptz3_cam != top_mic:
        send_win_command(command)

    current_mic = top_mic
    print(f'cs: {current_scene} - cm: {current_mic}')

    if target_scene == config.OBS_SCENES.PTZ2:
        ptz2_cam = current_mic
    else:
        ptz3_cam = current_mic

    set_scene(target_scene)
    time.sleep(POST_SWITCH_COOLDOWN)


# ==============================
# THREAD DE CAMERA
# ==============================
class CameraThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True

    def run(self):
        print("[CAM] Thread de camera iniciada.")
        while self.running:
            try:
                msg = control_to_camera.get(timeout=0.2)
            except Empty:
                continue

            if msg["type"] == "move":
                ptz = msg["ptz"]
                mic = msg["mic"]
                pan, tilt, zoom = config.MIC_POSITIONS[mic]

                print(f"[CAM] Movendo {ptz} para {mic} ({pan},{tilt},{zoom})")
                move_to_position(ptz, pan, tilt, zoom)
                camera_to_control.put(
                    {"type": "move_done", "ptz": ptz, "mic": mic}
                )


# ==============================
# THREAD DE STATUS DA CAMERA
# ==============================
class ControlThread(threading.Thread):
    def __init__(self, obs_controller):
        super().__init__(daemon=True)
        self.obs = obs_controller
        self.running = True

    def run(self):
        print("[CTRL] Thread de controle iniciada.")
        while self.running:
            try:
                msg = camera_to_control.get(timeout=0.2)
                if msg["type"] == "move_done":
                    print(f"[OBS] Movimento concluido: {msg}")
            except Empty:
                continue


def run_operational_loop():
    global current_mic

    obs.start_recording()
    wake_up()

    while dentro_do_horario():
        time.sleep(1)
        top_mic = get_latest_mic(timeout=0.1)

        if top_mic is NO_AUDIO_EVENT or top_mic is None or top_mic == current_mic:
            continue

        if top_mic == 'LOCUTOR':
            if mic_is_stable('LOCUTOR', LOCUTOR_CONFIRM_TIME):
                switch_to_locutor()
            continue

        if mic_is_stable(top_mic, GUEST_CONFIRM_TIME):
            switch_to_guest(top_mic)

    obs.stop_recording()


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    print("Iniciando sistema com threads...")

    mic_monitor = MicMonitor(config.MIC_DEVICES, callback=audio_callback)
    mic_monitor.start()

    obs = OBSController(config.OBS_HOST, config.OBS_PORT, config.OBS_PASSWORD)

    camera_thread = CameraThread()
    control_thread = ControlThread(obs)
    camera_thread.start()
    control_thread.start()

    send_win_command('alt+2')
    set_scene(config.OBS_SCENES.LOCUTOR)
    print('SISTEMA INICIADO')

    try:
        while True:
            if not dentro_do_horario():
                sleep()
                espera = max(0, int(segundos_ate_inicio()))

                print(f"\nFora do horario. Aguardando {espera} segundos...")
                time.sleep(espera)

                print(f"\nHora INICIO: {datetime.now().strftime('%H:%M:%S')}")
                send_win_command('alt+2')
                set_scene(config.OBS_SCENES.LOCUTOR)
                reset_runtime_state()

            print(f" Dentro do horario operacional ({INICIO} -> {FIM})")
            if dentro_do_horario():
                run_operational_loop()

            print(f"\nHora FIM: {datetime.now().strftime('%H:%M:%S')}")
            reset_runtime_state()
            set_scene(config.OBS_SCENES.STANDBY)

    except KeyboardInterrupt:
        print("\nEncerrando sistema...")
        mic_monitor.stop()
        obs.disconnect()
