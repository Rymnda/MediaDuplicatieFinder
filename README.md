# Media Duplicatie Finder

Desktop app for finding duplicate videos and photos on Windows.

## Features

- find duplicate videos using thumbnail/perceptual hash and duration comparison
- find duplicate photos using perceptual hash
- libraries and drives panel on the left side of the interface
- selection actions for duplicate groups
- export selection to TXT
- delete selected files to the Windows Recycle Bin
- language selection via `lang/*.json`
- intro video on startup with on/off setting
- video-based About window
- custom background, icon, and header logo assets

## Supported Languages

- English
- Nederlands
- Español
- Français
- Deutsch

On first launch the app defaults to English. After that, the last selected language is remembered.

## Requirements

- Python 3.10+
- Windows
- `ffmpeg` and `ffprobe` in `PATH` or at `C:\Program Files\FFMPEG\bin\`

## Installation

```powershell
pip install -r requirements.txt
python .\MediaDuplicatieFinder.py
```

## Build to EXE

Use the GitHub Actions workflow or run PyInstaller manually:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name "MediaDuplicatieFinder" --add-data "check_white.svg;." --add-data "lang;lang" MediaDuplicatieFinder.py
```

The build output will be placed in `dist\MediaDuplicatieFinder\`.

To include the current visual/media assets in the build, use:

```powershell
pyinstaller --noconfirm --windowed --name "MediaDuplicatieFinder" --icon "icon.ico" --add-data "check_white.svg;." --add-data "lang;lang" --add-data "BG.png;." --add-data "logo_flat.png;." --add-data "intro.mp4;." --add-data "Intro_about.mp4;." MediaDuplicatieFinder.py
```

## GitHub Repository Contents

Recommended files for the repository:

- `MediaDuplicatieFinder.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `BG.png`
- `check_white.svg`
- `icon.ico`
- `logo_flat.png`
- `intro.mp4`
- `Intro_about.mp4`
- `lang/`
- `LICENSE`
- `.github/workflows/build-windows.yml`

## GitHub Actions

After pushing to GitHub, the workflow automatically builds a Windows artifact with PyInstaller.

## Notes

- A license file is already included in this repository.
- If you also want to publish an installer, you can add Inno Setup later.
- If you update the visual assets, make sure your PyInstaller command or workflow includes them via `--add-data`.

## Author

RymndA
