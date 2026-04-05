# Media Duplicatie Finder

Desktop-app voor het vinden van dubbele video's en foto's op Windows.

## Functies

- dubbele video's vinden via thumbnail/perceptual hash en duurvergelijking
- dubbele foto's vinden via perceptual hash
- bibliotheken en schijven links in de interface
- selectieacties voor groepen
- export van selectie naar TXT
- verwijderen naar de Windows-prullenbak
- taalkeuze via `lang/*.json`

## Vereisten

- Python 3.10+
- Windows
- `ffmpeg` en `ffprobe` in `PATH` of op `C:\Program Files\FFMPEG\bin\`

## Installeren

```powershell
pip install -r requirements.txt
python .\MediaDuplicatieFinder.py
```

## Build naar exe

Lokale build:

```powershell
.\build_windows.bat
```

De build komt daarna in `dist\MediaDuplicatieFinder\`.

## GitHub upload

Aanbevolen bestanden voor de repository:

- `MediaDuplicatieFinder.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `check_white.svg`
- `check_white2.svg`
- `lang/`
- `.github/workflows/build-windows.yml`
- `build_windows.bat`

## GitHub Actions

Na pushen naar GitHub bouwt de workflow automatisch een Windows artifact met PyInstaller.

## Opmerkingen

- Kies nog zelf een licentie en voeg daarna bijvoorbeeld een `LICENSE`-bestand toe.
- Als je ook een installer wilt publiceren, kun je later Inno Setup toevoegen.

## Auteur

RymndA
