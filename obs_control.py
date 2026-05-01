import obsws_python as obs


class OBSController:
    """Controlador OBS para obsws-python >= 1.8 (WebSocket v5 SDK)."""

    def __init__(self, host="localhost", port=4455, password=""):
        try:
            self.client = obs.ReqClient(
                host=host,
                port=port,
                password=password,
                timeout=3,
            )
            version = self.client.get_version().obs_version
            print(f"[OBS] Conectado a {host}:{port} (OBS {version})")
        except Exception as e:
            print(f"[OBS] Falha ao conectar: {e}")
            self.client = None

    def start_recording(self):
        if not self.client:
            print("[OBS] Nao conectado, ignorando inicio da gravacao.")
            return
        try:
            self.client.start_record()
            print("[OBS] Gravando")
        except Exception as e:
            print(f"[OBS] Erro ao gravar: {e}")

    def stop_recording(self):
        if not self.client:
            print("[OBS] Nao conectado, ignorando fim da gravacao.")
            return
        try:
            self.client.stop_record()
            print("[OBS] Gravacao encerrada")
        except Exception as e:
            print(f"[OBS] Erro ao encerrar a gravacao: {e}")

    def set_scene(self, scene_name: str):
        if not self.client:
            print("[OBS] Nao conectado, ignorando troca de cena.")
            return
        try:
            self.client.set_current_program_scene(scene_name)
            print(f"[OBS] Cena alterada para: {scene_name}")
        except Exception as e:
            print(f"[OBS] Erro ao mudar cena: {e}")

    def disconnect(self):
        try:
            if self.client:
                self.client.disconnect()
                print("[OBS] Desconectado.")
        except Exception as e:
            print(f"[OBS] Erro ao desconectar: {e}")
