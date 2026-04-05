@echo off
setlocal
cd /d "%~dp0"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller ^
  --noconfirm ^
  --windowed ^
  --name "MediaDuplicatieFinder" ^
  --add-data "check_white.svg;." ^
  --add-data "check_white2.svg;." ^
  --add-data "lang;lang" ^
  MediaDuplicatieFinder.py

echo.
echo Build complete. See dist\MediaDuplicatieFinder\
endlocal
