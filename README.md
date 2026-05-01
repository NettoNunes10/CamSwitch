# CamSwitch

Automacao local para alternar cenas do OBS e controlar cameras OBSBOT a partir do microfone dominante.

## Requisitos

- Windows
- Python 3.10+
- OBS com obs-websocket habilitado
- OBSBOT Center aberto, com OSC em `UDP Server`, host `127.0.0.1` e porta `16284`
- Microfones configurados em `config.py`

## Instalacao

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Teste OSC da OBSBOT

Primeiro valide qual indice da camera responde:

```powershell
python test_obsbot_osc.py --device 2 --nudge
```

Teste movimento absoluto usando o controlador real:

```powershell
python test_obsbot_osc.py --device 2 --preset MIC2 --controller
```

## Executar o sistema

```powershell
python main.py
```

Os horarios, cenas do OBS, microfones e posicoes das cameras ficam em `config.py`.
