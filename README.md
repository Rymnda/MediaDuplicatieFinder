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

Local build:

```powershell
.\build_windows.bat
```

The build output will be placed in `dist\MediaDuplicatieFinder\`.

## GitHub Repository Contents

Recommended files for the repository:

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

After pushing to GitHub, the workflow automatically builds a Windows artifact with PyInstaller.

## Notes

- A license file is already included in this repository.
- If you also want to publish an installer, you can add Inno Setup later.

## Author

RymndA
