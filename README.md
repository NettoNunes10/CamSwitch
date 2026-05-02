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

Com `--device 1` ou `--device 2`, `--preset MIC1/MIC2/MIC3` tambem usa o `presets.json`, mapeando `device 1 -> PTZ1` e `device 2 -> PTZ2`.

Para testar exatamente os presets salvos pelo capturador/editor em `presets.json`:

```powershell
python test_obsbot_osc.py --camera PTZ1 --mic MIC1 --controller
python test_obsbot_osc.py --camera PTZ1 --mic MIC2 --controller
python test_obsbot_osc.py --camera PTZ1 --mic MIC3 --controller
python test_obsbot_osc.py --camera PTZ2 --mic MIC1 --controller
python test_obsbot_osc.py --camera PTZ2 --mic MIC2 --controller
python test_obsbot_osc.py --camera PTZ2 --mic MIC3 --controller
```

Se a camera se move mas nao bate exatamente com a posicao capturada, teste convencoes de eixo:

```powershell
python test_obsbot_osc.py --camera PTZ2 --mic MIC1 --controller --try-transforms
```

Quando uma variante bater, teste isoladamente:

```powershell
python test_obsbot_osc.py --camera PTZ2 --mic MIC1 --controller --transform invert-pan
```

Para comparar comando enviado com a posicao reportada depois do movimento:

```powershell
python preset_roundtrip.py --camera PTZ2 --mic MIC1
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
Para fazer a checagem e reinicio automaticamente:

```powershell
python obsbot_repair.py --ensure-osc --host 127.0.0.1 --port 16284
```

O `main.py` tambem faz essa verificacao no inicio quando `AUTO_REPAIR_OBSBOT_OSC = True` em `config.py`.

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
