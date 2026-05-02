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

Diagnostico de OSC quando o OBSBOT Center para de responder:

```powershell
python osc_diagnose.py --device 2
```

Esse comando verifica se existe listener UDP na porta configurada, envia a sequencia usada pelo layout TouchOSC oficial e imprime qualquer resposta OSC recebida.
Se o OBSBOT Center mostrar algo como `osc.udp://NOME-DO-PC:16284/` no log, teste tambem:

```powershell
python osc_diagnose.py --device 2 --host NOME-DO-PC
python osc_diagnose.py --device 2 --scan-hosts
```

Se o log do OBSBOT Center nao mostrar mais `OSC URL` ou `start osc init`, colete status/reset seguro:

```powershell
python obsbot_repair.py --status
python obsbot_repair.py --kill --backup-config --reset-config
```

Depois abra o OBSBOT Center de novo, reative OSC e rode `python osc_diagnose.py --device 2`.
Se a tela mostrar OSC configurado mas `global.ini` tiver `OSC=false`, ative diretamente:

```powershell
python obsbot_repair.py --kill --enable-osc --host 127.0.0.1 --port 16284
```

Depois abra o OBSBOT Center e confira se o log mostra `OSC URL`.

## Editor de presets

Com o OBSBOT Center aberto e OSC ativo, rode:

```powershell
python preset_editor.py
```

Escolha `PTZ1` ou `PTZ2`, mova a camera, ajuste `pan`, `tilt` e `zoom`, e clique em `Salvar preset`.
Os valores ficam em `presets.json` e sao carregados automaticamente pelo sistema.

Se preferir ajustar a camera pelo proprio OBSBOT Center e apenas tentar capturar a posicao atual:

```powershell
python preset_capture.py
```

Escolha a PTZ e o microfone, ajuste pan/tilt/zoom no OBSBOT Center e clique em `Capturar atual`.
O programa registra as respostas OSC no log e salva em `presets.json` quando conseguir ler pan/tilt.

## Executar o sistema

```powershell
python main.py
```

Os horarios, cenas do OBS, microfones e posicoes das cameras ficam em `config.py`.
