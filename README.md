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
- custom assets from `assets/`

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
C:\Users\ansem\Documents\Github\_venvs\venv_cuda_py310_np2\Scripts\python.exe -m PyInstaller --clean MediaDuplicatieFinder.spec
```

The build output will be placed in `dist\`.

## GitHub Repository Contents

Recommended files for the repository:

- `MediaDuplicatieFinder.py`
- `requirements.txt`
- `README.md`
- `.gitignore`
- `assets/`
- `lang/`
- `LICENSE`
- `.github/workflows/build-windows.yml`

## GitHub Actions

After pushing to GitHub, the workflow automatically builds a Windows artifact with PyInstaller.

## Notes

- A license file is already included in this repository.
- If you also want to publish an installer, you can add Inno Setup later.
- If you update visual or media files, keep them in `assets/`.

## Author

RymndA
