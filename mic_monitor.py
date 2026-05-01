# mic_monitor_by_name.py
import threading
import sounddevice as sd
import numpy as np
import time

THRESHOLD = 0.01  # nível mínimo para considerar um mic ativo

def get_rms(data):
    return float(np.sqrt(np.mean(np.square(data)))) if len(data) else 0.0

class MicMonitor(threading.Thread):
    def __init__(self, mic_devices, callback, interval=0.1):
        super().__init__(daemon=True)
        self.mic_devices = mic_devices
        self.callback = callback
        self.interval = interval
        self.running = True
        self.streams = {}
        self.sample_rate = 32000
        self.chunk = int(self.sample_rate * self.interval)

        # Abre streams de cada mic pelo nome + host API
        all_devices = sd.query_devices()
        host_apis = {i: h['name'] for i, h in enumerate(sd.query_hostapis())}

        for mic_name, (dev_name, dev_api) in mic_devices.items():
            # encontra o índice correto do dispositivo
            dev_index = None
            for idx, dev in enumerate(all_devices):
                if dev['name'].startswith(dev_name) and host_apis[dev['hostapi']] == dev_api:
                    dev_index = idx
                    break
            if dev_index is None:
                print(f"[WARN] Mic '{mic_name}' não encontrado.")
                continue

            try:
                stream = sd.InputStream(device=dev_index, channels=1,
                                        samplerate=self.sample_rate, dtype='float32')
                stream.start()
                self.streams[mic_name] = stream
            except Exception as e:
                print(f"[ERROR] Falha ao abrir stream para '{mic_name}': {e}")

    def run(self):
        while self.running:
            levels = {}
            for mic_name, stream in self.streams.items():
                try:
                    data, overflowed = stream.read(self.chunk)
                    levels[mic_name] = get_rms(data)
                except Exception:
                    levels[mic_name] = 0.0

            if levels:
                top_mic = max(levels, key=levels.get)

                if levels[top_mic] >= THRESHOLD:
                    # print(f'top mic: {top_mic} - level: {levels[top_mic]}')
                    self.callback(top_mic)
                else:
                    self.callback(None)  # nenhum mic acima do limiar

            time.sleep(self.interval)

    def stop(self):
        self.running = False
        for stream in self.streams.values():
            try:
                stream.stop()
                stream.close()
            except:
                pass
