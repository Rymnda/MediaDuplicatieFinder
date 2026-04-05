#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys

# Media Duplicatie Finder


import os
import ctypes
import json

import subprocess
import tempfile
import hashlib
import shutil
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

import numpy as np
from PIL import Image
import imagehash
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6 import QtMultimedia, QtMultimediaWidgets
except ImportError as e:
    print(f"CRITICAL: Ontbrekende modules in actieve omgeving.\nFout: {e}")
    print("Gebruik bijvoorbeeld: pip install pyside6 pillow imagehash numpy")
    sys.exit(1)

# ===================== USER-TUNABLE SETTINGS =====================
FFMPEG_PATHS = [shutil.which("ffmpeg"), r"C:\\Program Files\\FFMPEG\\bin\\ffmpeg.exe"]
FFPROBE_PATHS = [shutil.which("ffprobe"), r"C:\\Program Files\\FFMPEG\\bin\\ffprobe.exe"]

THUMB_POS_SEC = 1         # tijdstip voor videothumbs in seconden
PHASH_TOL_VIDEO = 8       # 0..64 (lager = strenger) voor video
PHASH_TOL_PHOTO = 6       # strenger voor foto's
DUR_TOL_SEC = 1.5         # toegestane duurverschil in seconden (video)

QUALITY_WEIGHTS = dict(
    res=3.0,
    bpp=1.0,
    br=1.5,
    sharp=0.5,
)
# ================================================================

APP_NAME = "Media Duplicatie Finder"
ORG = "RymndA"
APP_SETTINGS_NAME = "Media Duplicatie Finder 2026"
SET_KEY_LAST_VIDEO = "last_root_video"
SET_KEY_LAST_PHOTO = "last_root_photo"
SET_KEY_LANGUAGE = "ui_language"
SET_KEY_PLAY_INTRO = "play_intro_on_startup"
VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
DEFAULT_LANGUAGE_OPTIONS = [
    {"code": "en", "label": "English"},
    {"code": "nl", "label": "Nederlands"},
    {"code": "es", "label": "Español"},
    {"code": "fr", "label": "Français"},
    {"code": "de", "label": "Deutsch"},
]
DEFAULT_TRANSLATIONS = {
    "app_title_suffix": "Video and photo duplicates",
    "menu_file": "File",
    "menu_settings": "Settings",
    "menu_language": "Language",
    "menu_help": "Help",
    "action_exit": "Exit",
    "action_about": "About / Info",
    "action_scripts": "Scripts and modules",
    "action_recurse_video": "Video: include subfolders by default",
    "action_recurse_photo": "Photo: include subfolders by default",
    "action_play_intro": "Play intro on startup",
    "tab_video": "Video duplicates",
    "tab_photo": "Photo duplicates",
    "footer_ready": "Ready",
    "footer_language": "Language",
    "label_libraries": "Libraries",
    "label_drives": "This PC / Drives",
    "label_selected_folder": "Selected folder",
    "placeholder_folder": "Drop a folder here or choose on the left",
    "checkbox_subfolders": "Include subfolders",
    "checkbox_remember": "Remember this folder",
    "button_scan": "Scan",
    "button_browse": "Browse...",
    "button_select_all": "Select all",
    "button_deselect_all": "Deselect all",
    "button_invert_selection": "Invert selection",
    "button_select_others": "Select others",
    "button_select_all_except_first": "Select ALL except first",
    "button_export_txt": "Export selection to TXT",
    "button_delete_selection": "Delete selection",
    "button_undo": "Undo last action",
    "button_quick_move": "Quick: move selected",
    "button_keep_best": "Keep best per group",
    "about_body": "Media audit for video and photo duplicates.\nExport and recycle bin support available.",
    "about_language": "Selected language",
    "about_author": "Author / GitHub",
    "scripts_title": "Scripts and modules",
    "scripts_main": "Main script",
    "scripts_modules": "Modules",
    "scripts_tools": "Tools",
    "scripts_github": "GitHub",
}


def _first_existing(paths: List[Optional[str]]) -> Optional[str]:
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


FFMPEG = _first_existing(FFMPEG_PATHS)
FFPROBE = _first_existing(FFPROBE_PATHS)


def language_dir_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "lang")


def load_language_options() -> List[Dict[str, str]]:
    return list(DEFAULT_LANGUAGE_OPTIONS)


def translation_file_path(code: str) -> str:
    return os.path.join(language_dir_path(), f"{code}.json")


def load_translations(code: str) -> Dict[str, str]:
    translations = dict(DEFAULT_TRANSLATIONS)
    path = translation_file_path(code)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                for key, value in loaded.items():
                    translations[str(key)] = str(value)
        except Exception:
            pass
    return translations


def resource_path(name: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    asset_path = os.path.join(base_dir, "assets", name)
    if os.path.exists(asset_path):
        return asset_path
    return os.path.join(base_dir, name)


class WatermarkWidget(QtWidgets.QWidget):
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self._pixmap = QtGui.QPixmap(image_path) if os.path.exists(image_path) else QtGui.QPixmap()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        if self._pixmap.isNull():
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.setOpacity(0.1)

        available = self.rect().adjusted(24, 24, -24, -24)
        scaled = self._pixmap.scaled(
            available.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        x = available.x() + (available.width() - scaled.width()) // 2
        y = available.y() + (available.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


class IntroDialog(QtWidgets.QDialog):
    def __init__(self, video_path: str, icon_path: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            QtCore.Qt.Dialog
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.resize(960, 540)
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QtWidgets.QFrame()
        frame.setObjectName("introFrame")
        frame.setStyleSheet(
            "#introFrame { background: #050814; border: 1px solid #1d2a3e; border-radius: 24px; }"
        )
        inner = QtWidgets.QVBoxLayout(frame)
        inner.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QtMultimediaWidgets.QVideoWidget()
        self.video_widget.setStyleSheet("background: #050814; border-radius: 24px;")
        inner.addWidget(self.video_widget)
        outer.addWidget(frame)

        self.audio_output = QtMultimedia.QAudioOutput(self)
        self.audio_output.setMuted(False)
        self.audio_output.setVolume(1.0)
        self.player = QtMultimedia.QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_media_error)
        self.player.durationChanged.connect(self._on_duration_changed)
        self._stop_timer = QtCore.QTimer(self)
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self.accept)

        if os.path.exists(video_path):
            self.player.setSource(QtCore.QUrl.fromLocalFile(video_path))
        else:
            QtCore.QTimer.singleShot(10, self.accept)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._apply_round_mask()
        QtCore.QTimer.singleShot(0, self._start)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_round_mask()

    def _apply_round_mask(self):
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect()), 24, 24)
        region = QtGui.QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def _start(self):
        if self.player.source().isEmpty():
            self.accept()
            return
        self.player.play()

    def _on_media_status_changed(self, status):
        if status == QtMultimedia.QMediaPlayer.EndOfMedia:
            self.accept()
        elif status == QtMultimedia.QMediaPlayer.InvalidMedia:
            self.accept()

    def _on_duration_changed(self, duration_ms: int):
        if duration_ms > 0:
            self._stop_timer.start(max(1, duration_ms // 2))

    def _on_media_error(self, *_args):
        self.accept()


class AboutVideoDialog(QtWidgets.QDialog):
    def __init__(self, video_path: str, icon_path: str, title_text: str, left_text: str, right_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Info / Over")
        self.resize(960, 740)
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        frame = QtWidgets.QFrame()
        frame.setObjectName("aboutVideoFrame")
        frame.setStyleSheet(
            "#aboutVideoFrame { background: #0b1120; border: 1px solid #1d2a3e; }"
        )
        root.addWidget(frame)

        frame_layout = QtWidgets.QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        video_host = QtWidgets.QWidget()
        video_host.setStyleSheet("background: #0b1120;")
        video_stack = QtWidgets.QStackedLayout(video_host)
        video_stack.setContentsMargins(0, 0, 0, 0)
        video_stack.setStackingMode(QtWidgets.QStackedLayout.StackAll)

        self.video_widget = QtMultimediaWidgets.QVideoWidget()
        self.video_widget.setStyleSheet("background: #0b1120;")
        video_stack.addWidget(self.video_widget)

        close_btn = QtWidgets.QPushButton("OK")
        close_btn.setMinimumWidth(118)
        close_btn.clicked.connect(self.accept)

        bottom_bar = QtWidgets.QWidget()
        bottom_bar.setFixedHeight(190)
        bottom_bar.setStyleSheet("background: #000000;")
        bottom_layout = QtWidgets.QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(22, 16, 22, 16)
        bottom_layout.setSpacing(16)

        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(8)

        title = QtWidgets.QLabel(title_text)
        title.setStyleSheet("color: white; font-size: 16pt; font-weight: 700;")
        title.setWordWrap(True)

        left_body = QtWidgets.QLabel(left_text)
        left_body.setStyleSheet("color: #d7e6fb; font-size: 10.5pt;")
        left_body.setWordWrap(True)
        left_body.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        right_body = QtWidgets.QLabel(right_text)
        right_body.setStyleSheet("color: #d7e6fb; font-size: 10.5pt;")
        right_body.setWordWrap(True)
        right_body.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

        left_col.addWidget(title)
        left_col.addWidget(left_body, 1)

        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(8)
        right_col.addSpacing(34)
        right_col.addWidget(right_body, 1)

        columns = QtWidgets.QHBoxLayout()
        columns.setSpacing(28)
        columns.addLayout(left_col, 1)
        columns.addLayout(right_col, 1)

        bottom_layout.addLayout(columns, 1)
        bottom_layout.addWidget(close_btn, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)

        frame_layout.addWidget(video_host, 1)
        frame_layout.addWidget(bottom_bar, 0)

        self.audio_output = QtMultimedia.QAudioOutput(self)
        self.audio_output.setMuted(True)
        self.player = QtMultimedia.QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.setLoops(QtMultimedia.QMediaPlayer.Loops.Infinite)

        if os.path.exists(video_path):
            self.player.setSource(QtCore.QUrl.fromLocalFile(video_path))

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if not self.player.source().isEmpty():
            self.player.play()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.player.stop()
        super().closeEvent(event)


def thumb_cache_path(path: str) -> str:
    h = hashlib.sha1(path.encode("utf-8", "ignore")).hexdigest()
    d = os.path.join(tempfile.gettempdir(), "MediaDuplicatieFinder_cache")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{h}.jpg")


def make_video_thumbnail(path: str, outpath: str, t_sec: int = THUMB_POS_SEC) -> bool:
    if not FFMPEG:
        return False
    try:
        cmd = [FFMPEG, "-y", "-ss", str(t_sec), "-i", path, "-frames:v", "1", "-q:v", "3", outpath]
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 if os.name == "nt" else 0,
            check=True,
        )
        return os.path.exists(outpath)
    except Exception:
        return False


def make_image_thumbnail(path: str, outpath: str, max_w: int = 480) -> bool:
    try:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        if w > max_w:
            scale = max_w / float(w)
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        im.save(outpath, format="JPEG", quality=90)
        return True
    except Exception:
        return False


def ffprobe_json(path: str) -> Dict:
    if not FFPROBE:
        return {}
    try:
        cmd = [
            FFPROBE,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            path,
        ]
        out = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        import json
        return json.loads(out.decode("utf-8", "ignore"))
    except Exception:
        return {}


def parse_meta(info: Dict) -> Tuple[float, int, int, Optional[float]]:
    dur = 0.0
    w = 0
    h = 0
    br = None
    try:
        fmt = info.get("format") or {}
        if "duration" in fmt:
            dur = float(fmt["duration"])
        if "bit_rate" in fmt:
            br = float(fmt["bit_rate"])
        for s in info.get("streams", []):
            if s.get("codec_type") == "video":
                w = int(s.get("width") or 0)
                h = int(s.get("height") or 0)
                if not br and s.get("bit_rate"):
                    br = float(s["bit_rate"])
                break
    except Exception:
        pass
    return dur, w, h, br


def human_size(n: int) -> str:
    step = 1024.0
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < step:
            return f"{n:.0f} {u}"
        n /= step
    return f"{n:.0f} PB"


def move_to_recycle_bin(path: str) -> None:
    if os.name != "nt":
        raise OSError("Prullenbakactie is alleen beschikbaar op Windows.")

    FO_DELETE = 3
    FOF_ALLOWUNDO = 0x0040
    FOF_NOCONFIRMATION = 0x0010
    FOF_NOERRORUI = 0x0400
    FOF_SILENT = 0x0004

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("wFunc", ctypes.c_uint),
            ("pFrom", ctypes.c_wchar_p),
            ("pTo", ctypes.c_wchar_p),
            ("fFlags", ctypes.c_ushort),
            ("fAnyOperationsAborted", ctypes.c_int),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", ctypes.c_wchar_p),
        ]

    op = SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = path + "\0\0"
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if result != 0:
        raise OSError(f"SHFileOperationW foutcode {result}")


@dataclass
class VidMeta:
    path: str
    size: int
    mtime: float
    dur: float
    w: int
    h: int
    bitrate: float | None
    phash: Optional[imagehash.ImageHash]
    thumb: Optional[str]
    quality: float
    is_video: bool = True

    @property
    def area(self) -> int:
        return max(1, self.w * self.h)

    @property
    def name(self) -> str:
        return os.path.basename(self.path)


def calc_quality(vm: VidMeta) -> float:
    area = max(1, vm.area)
    bpp = float(vm.size) / float(area)
    br_score = 0.0 if not vm.bitrate else min(vm.bitrate / 1_000_000.0, 25.0)
    sharp_score = 0.0
    try:
        if vm.phash is not None:
            ones = bin(int(str(vm.phash), 16)).count("1")
            sharp_score = ones / 64.0
    except Exception:
        pass
    w = QUALITY_WEIGHTS
    return (
        (vm.area / 1_000_000.0) * w["res"]
        + min(bpp, 5.0) * w["bpp"]
        + br_score * w["br"]
        + sharp_score * w["sharp"]
    )


# ---------- Clustering ----------


class DSU:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        if self.r[ra] == self.r[rb]:
            self.r[ra] += 1


def cluster_videos(
    items: List[VidMeta],
    phash_tol: int = PHASH_TOL_VIDEO,
    dur_tol: float = DUR_TOL_SEC,
) -> List[List[VidMeta]]:
    n = len(items)
    if n <= 1:
        return []
    dsu = DSU(n)
    buckets: Dict[int, List[int]] = {}
    for i, m in enumerate(items):
        key = int(round(m.dur / dur_tol))
        buckets.setdefault(key, []).append(i)
        buckets.setdefault(key - 1, []).append(i)
        buckets.setdefault(key + 1, []).append(i)

    for idxs in buckets.values():
        L = len(idxs)
        for ii in range(L):
            i = idxs[ii]
            mi = items[i]
            for jj in range(ii + 1, L):
                j = idxs[jj]
                mj = items[j]
                if abs(mi.dur - mj.dur) > dur_tol:
                    continue
                if mi.phash is None or mj.phash is None:
                    continue
                try:
                    if (mi.phash - mj.phash) <= phash_tol:
                        dsu.union(i, j)
                except Exception:
                    continue

    groups_map: Dict[int, List[VidMeta]] = {}
    for i in range(n):
        r = dsu.find(i)
        groups_map.setdefault(r, []).append(items[i])

    groups = [
        sorted(
            g,
            key=lambda m: (-m.quality, -m.area, -(m.bitrate or 0), -m.size),
        )
        for g in groups_map.values()
        if len(g) >= 2
    ]
    groups.sort(
        key=lambda g: (-g[0].quality, -g[0].area, -(g[0].bitrate or 0), -g[0].size)
    )
    return groups


def cluster_images(
    items: List[VidMeta],
    phash_tol: int = PHASH_TOL_PHOTO,
) -> List[List[VidMeta]]:
    n = len(items)
    if n <= 1:
        return []
    dsu = DSU(n)

    for i in range(n):
        mi = items[i]
        if mi.phash is None:
            continue
        for j in range(i + 1, n):
            mj = items[j]
            if mj.phash is None:
                continue
            area_i, area_j = mi.area, mj.area
            if area_i == 0 or area_j == 0:
                continue
            ratio = max(area_i, area_j) / min(area_i, area_j)
            if ratio > 4.0:
                continue
            try:
                if (mi.phash - mj.phash) <= phash_tol:
                    dsu.union(i, j)
            except Exception:
                continue

    groups_map: Dict[int, List[VidMeta]] = {}
    for i in range(n):
        r = dsu.find(i)
        groups_map.setdefault(r, []).append(items[i])

    groups = [
        sorted(
            g,
            key=lambda m: (-m.quality, -m.area, -m.size),
        )
        for g in groups_map.values()
        if len(g) >= 2
    ]
    groups.sort(
        key=lambda g: (-g[0].quality, -g[0].area, -g[0].size),
    )
    return groups


# ---------- GUI (Ultimate / Sarah 2 theme) ----------
class DarkPalette:
    @staticmethod
    def stylesheet() -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(base_dir, "assets")
        check_svg_path = os.path.join(assets_dir, "check_white.svg")

        if not os.path.exists(check_svg_path):
            svg_data = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M5 13l4 4L19 7" fill="none" stroke="#ffffff" stroke-width="3"
        stroke-linecap="round" stroke-linejoin="round" />
</svg>
"""
            try:
                os.makedirs(assets_dir, exist_ok=True)
                check_svg_path = os.path.join(assets_dir, "check_white.svg")
                with open(check_svg_path, "w", encoding="utf-8") as f:
                    f.write(svg_data.strip() + "\n")
            except OSError:
                check_svg_path = ""

        check_svg_url = check_svg_path.replace("\\", "/") if check_svg_path else ""
        image_rule = f'image: url("{check_svg_url}");' if check_svg_url else ""

        return f"""
        QWidget {{
            background-color: #050814;
            color: #E6EEF8;
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 10pt;
        }}

        QMenuBar {{
            background-color: #050814;
            color: #E6EEF8;
            border-bottom: 1px solid #151b2c;
        }}
        QMenuBar::item {{
            padding: 4px 12px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background: #1e2b40;
        }}
        QMenu {{
            background-color: #050b16;
            color: #E6EEF8;
            border: 1px solid #1b2233;
        }}
        QMenu::item {{
            padding: 4px 18px;
        }}
        QMenu::item:selected {{
            background: #2b3a55;
        }}

        QTabWidget::pane {{
            border: 1px solid #1d2a3e;
            border-radius: 12px;
            margin-top: 4px;
        }}
        QTabBar::tab {{
            background: #060c18;
            padding: 6px 18px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            margin-right: 4px;
            color: #9fb3d9;
        }}
        QTabBar::tab:selected {{
            background: #182235;
            color: #E6EEF8;
        }}
        QTabBar::tab:hover {{
            background: #1f2c44;
        }}

        QLineEdit {{
            background: #0f1620;
            border: 2px dashed rgba(140,180,255,0.35);
            padding: 10px 12px;
            border-radius: 10px;
        }}
        QLineEdit:focus {{
            border: 2px solid #2d7bff;
        }}

        QPushButton {{
            background: #172237;
            border: 1px solid #2b3b5c;
            padding: 8px 16px;
            border-radius: 10px;
            color: #E6EEF8;
        }}
        QPushButton:hover {{
            background: #1f2d46;
        }}
        QPushButton:disabled {{
            background: #111726;
            color: #4b5770;
            border-color: #1a2235;
        }}
        QPushButton.danger {{
            background: #3e1212;
            border: 1px solid #6b1f1f;
            color: #ffcccc;
        }}
        QPushButton.danger:hover {{
            background: #5c1818;
        }}

        QCheckBox {{
            spacing: 8px;
        }}
        /* --- CHECKBOX STYLING --- */
        QCheckBox::indicator {{
            width: 18px; height: 18px;
            border-radius: 4px;
            border: 2px solid #3e4a61;
            background: #0f1620;
        }}
        QCheckBox::indicator:hover {{
            border-color: #2d7bff;
        }}
        QCheckBox::indicator:checked {{
            background-color: transparent;
            border-color: #2d7bff;
            {image_rule}
        }}
        /* ------------------------ */

        QHeaderView::section {{
            background: #151F2E;
            color: #E6EEF8;
            padding: 8px;
            border: 0;
            border-right: 1px solid #24344d;
            border-bottom: 1px solid #24344d;
        }}

        QScrollArea {{
            background: #111827;
            border: 1px solid #1d2a3e;
            border-radius: 12px;
        }}

        QTreeView {{
            background: #111827;
            border: none;
            outline: none;
        }}
        QTreeView::item {{
            background: transparent;
            padding: 1px 4px;
        }}
        QTreeView::item:selected {{
            background: #2b3a55;
        }}
        QTreeView::item:hover {{
            background: #1f2d46;
        }}

        QFrame.card {{
            background: #111827;
            border-radius: 12px;
            border: 1px solid #1d2a3e;
        }}
        QFrame.panel {{
            background: #111827;
            border-radius: 12px;
            border: 1px solid #1d2a3e;
        }}
        QWidget#resultsInner {{
            background: #111827;
        }}
        QListWidget {{
            background: #111827;
            border: none;
            outline: none;
            padding: 4px;
        }}
        QListWidget::item {{
            background: transparent;
            border-radius: 6px;
            padding: 4px 8px;
            margin: 1px 0;
        }}
        QListWidget::item:selected {{
            background: #2b3a55;
        }}
        QListWidget::item:hover {{
            background: #1f2d46;
        }}

        QLabel.hint {{
            color: #9CCFF2;
        }}
        QLabel.sectionTitle {{
            color: #8FD3FE;
            font-weight: 600;
            font-size: 10pt;
            margin-bottom: 2px;
        }}

        QProgressBar {{
            background: #050b16;
            border: 1px solid #1d2a3e;
            border-radius: 6px;
            text-align: center;
            padding: 1px;
        }}
        QProgressBar::chunk {{
            background-color: #2d7bff;
            border-radius: 6px;
        }}
        """



class DropLineEdit(QtWidgets.QLineEdit):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dropEvent(self, e: QtGui.QDropEvent):
        urls = e.mimeData().urls()
        if not urls:
            return
        p = urls[0].toLocalFile()
        if os.path.isfile(p):
            p = os.path.dirname(p)
        if os.path.isdir(p):
            self.setText(p)


def load_image_scaled(path: str, max_w: int = 260) -> QtGui.QPixmap:
    try:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        scale = min(1.0, max_w / float(w))
        if scale < 1.0:
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        qimg = QtGui.QImage(
            im.tobytes(),
            im.width,
            im.height,
            im.width * 3,
            QtGui.QImage.Format_RGB888,
        )
        return QtGui.QPixmap.fromImage(qimg)
    except Exception:
        return QtGui.QPixmap()


class ThumbCard(QtWidgets.QFrame):
    def __init__(self, vm: VidMeta):
        super().__init__()
        self.vm = vm
        self.setProperty("class", "card")
        self.setMinimumWidth(280)

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)

        self.chk = QtWidgets.QCheckBox(vm.name)
        self.chk.setTristate(False)

        self.thumb_lbl = QtWidgets.QLabel()
        self.thumb_lbl.setAlignment(QtCore.Qt.AlignCenter)
        if vm.thumb and os.path.exists(vm.thumb):
            self.thumb_lbl.setPixmap(load_image_scaled(vm.thumb, 260))

        if vm.is_video:
            info_text = f"{vm.w}×{vm.h} • {human_size(vm.size)} • {vm.dur:.1f}s • Q={vm.quality:.2f}"
        else:
            info_text = f"{vm.w}×{vm.h} • {human_size(vm.size)} • Q={vm.quality:.2f}"

        info = QtWidgets.QLabel(info_text)
        info.setProperty("class", "hint")

        btn_row = QtWidgets.QHBoxLayout()
        btn_open = QtWidgets.QPushButton("Open map")
        btn_open.clicked.connect(self.open_folder)
        btn_play = QtWidgets.QPushButton("Open bestand")
        btn_play.clicked.connect(self.open_file)
        btn_row.addWidget(btn_open)
        btn_row.addWidget(btn_play)

        v.addWidget(self.chk)
        v.addWidget(self.thumb_lbl)
        v.addWidget(info)
        v.addLayout(btn_row)

    def open_folder(self):
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(os.path.dirname(self.vm.path))
        )

    def open_file(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.vm.path))


class DetailRow(QtWidgets.QFrame):
    def __init__(self, vm: VidMeta, is_best: bool):
        super().__init__()
        self.vm = vm
        self.setProperty("class", "card")

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(4)

        self.chk = QtWidgets.QCheckBox()

        best_lbl = QtWidgets.QLabel("Beste" if is_best else "")
        best_lbl.setStyleSheet("color:#8FD3FE;font-weight:600;")

        name_lbl = QtWidgets.QLabel(vm.name)
        name_lbl.setStyleSheet("font-weight:600;")
        name_lbl.setWordWrap(True)

        if vm.is_video:
            meta_text = (
                f"{vm.w}x{vm.h} | {human_size(vm.size)} | {vm.dur:.1f}s | "
                f"Q={vm.quality:.2f}"
            )
        else:
            meta_text = f"{vm.w}x{vm.h} | {human_size(vm.size)} | Q={vm.quality:.2f}"

        meta_lbl = QtWidgets.QLabel(meta_text)
        meta_lbl.setProperty("class", "hint")

        path_lbl = QtWidgets.QLabel(vm.path)
        path_lbl.setProperty("class", "hint")
        path_lbl.setWordWrap(True)

        btn_open = QtWidgets.QPushButton("Open bestand")
        btn_open.clicked.connect(self.open_file)
        btn_folder = QtWidgets.QPushButton("Open map")
        btn_folder.clicked.connect(self.open_folder)

        btns = QtWidgets.QHBoxLayout()
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(8)
        btns.addWidget(btn_open)
        btns.addWidget(btn_folder)
        btns.addStretch(1)

        layout.addWidget(self.chk, 0, 0, 2, 1, QtCore.Qt.AlignTop)
        layout.addWidget(best_lbl, 0, 1, 1, 1, QtCore.Qt.AlignTop)
        layout.addWidget(name_lbl, 0, 2, 1, 1)
        layout.addWidget(meta_lbl, 1, 2, 1, 1)
        layout.addWidget(path_lbl, 2, 1, 1, 2)
        layout.addLayout(btns, 3, 1, 1, 2)
        layout.setColumnStretch(2, 1)

    def open_folder(self):
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(os.path.dirname(self.vm.path))
        )

    def open_file(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.vm.path))


class GroupRow(QtWidgets.QFrame):
    def __init__(self, items: List[VidMeta], is_photo: bool = False):
        super().__init__()
        self.items = items
        self.is_photo = is_photo
        self.setProperty("class", "card")
        self.cards: List[ThumbCard] = []
        self.detail_rows: List[DetailRow] = []

        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        head = QtWidgets.QHBoxLayout()
        label_kind = "Foto-groep" if is_photo else "Video-groep"
        title = QtWidgets.QLabel(f"{label_kind} • {len(items)} items • beste: {items[0].name}")
        title.setStyleSheet("color:#8FD3FE;font-weight:600")

        btn_best = QtWidgets.QPushButton("Selecteer beste")
        btn_best.clicked.connect(self.sel_best_only)
        btn_except = QtWidgets.QPushButton("Alles behalve 1e")
        btn_except.clicked.connect(self.sel_except_first)
        btn_move_others = QtWidgets.QPushButton("Beste houden → verplaats overige…")
        btn_move_others.clicked.connect(self.move_others_dialog)

        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(btn_best)
        head.addWidget(btn_except)
        head.addWidget(btn_move_others)

        v.addLayout(head)

        self.views = QtWidgets.QStackedWidget()

        thumb_page = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(thumb_page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for m in items:
            c = ThumbCard(m)
            self.cards.append(c)
            row.addWidget(c)
        row.addStretch(1)
        self.views.addWidget(thumb_page)

        details_page = QtWidgets.QWidget()
        details_layout = QtWidgets.QVBoxLayout(details_page)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(8)
        for i, m in enumerate(items):
            detail = DetailRow(m, is_best=(i == 0))
            self.detail_rows.append(detail)
            details_layout.addWidget(detail)
        details_layout.addStretch(1)
        self.views.addWidget(details_page)

        for card, detail in zip(self.cards, self.detail_rows):
            card.chk.toggled.connect(
                lambda checked, peer=detail.chk: self._sync_checkbox(peer, checked)
            )
            detail.chk.toggled.connect(
                lambda checked, peer=card.chk: self._sync_checkbox(peer, checked)
            )

        v.addWidget(self.views)

    def _sync_checkbox(self, checkbox: QtWidgets.QCheckBox, checked: bool):
        if checkbox.isChecked() == checked:
            return
        blocker = QtCore.QSignalBlocker(checkbox)
        checkbox.setChecked(checked)
        del blocker

    def set_view_mode(self, mode: str):
        self.views.setCurrentIndex(0 if mode == "thumbnails" else 1)

    def selected_paths(self) -> List[str]:
        return [c.vm.path for c in self.cards if c.chk.isChecked()]

    def sel_best_only(self):
        for i, c in enumerate(self.cards):
            c.chk.setChecked(i == 0)

    def sel_except_first(self):
        for i, c in enumerate(self.cards):
            c.chk.setChecked(i != 0)

    def move_others_dialog(self):
        dest = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Kies doelmap voor overige"
        )
        if not dest:
            return
        keep_dir = os.path.join(dest, "origineel")
        os.makedirs(dest, exist_ok=True)
        os.makedirs(keep_dir, exist_ok=True)
        moved = 0
        best_path = self.items[0].path if self.items else None
        for c in self.cards:
            p = c.vm.path
            try:
                if p == best_path:
                    shutil.move(p, os.path.join(keep_dir, os.path.basename(p)))
                else:
                    shutil.move(p, os.path.join(dest, os.path.basename(p)))
                moved += 1
            except Exception as e:
                print("Move fail:", p, e)
        QtWidgets.QMessageBox.information(
            self,
            "Klaar",
            f"{moved} bestand(en) verplaatst.\nDoel: {dest}\nOrigineel: {keep_dir}",
        )


# ---------- Workers ----------


class VideoScanWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)
    finished = QtCore.Signal(list)

    def __init__(self, root: str, recurse: bool):
        super().__init__()
        self.root = root
        self.recurse = recurse
        self._abort = False

    @QtCore.Slot()
    def run(self):
        files: List[str] = []
        if self.recurse:
            for r, _, names in os.walk(self.root):
                for n in names:
                    if os.path.splitext(n)[1].lower() in VIDEO_EXTS:
                        files.append(os.path.join(r, n))
        else:
            for n in os.listdir(self.root):
                p = os.path.join(self.root, n)
                if os.path.isfile(p) and os.path.splitext(n)[1].lower() in VIDEO_EXTS:
                    files.append(p)

        total = len(files)
        metas: List[VidMeta] = []
        for i, p in enumerate(files, 1):
            if self._abort: break
            try:
                st = os.stat(p)
                info = ffprobe_json(p)
                dur, w, h, br = parse_meta(info)
                tpath = thumb_cache_path(p)
                if not os.path.exists(tpath):
                    make_video_thumbnail(p, tpath, THUMB_POS_SEC)
                ph = None
                if os.path.exists(tpath):
                    try:
                        im = Image.open(tpath).convert("RGB")
                        im.load()
                        ph = imagehash.phash(im)
                    except Exception: pass
                vm = VidMeta(p, st.st_size, st.st_mtime, dur, w, h, br, ph, tpath if os.path.exists(tpath) else None, 0.0, True)
                vm.quality = calc_quality(vm)
                metas.append(vm)
            except Exception: pass
            self.progress.emit(i, total)

        groups = cluster_videos(metas, PHASH_TOL_VIDEO, DUR_TOL_SEC)
        self.finished.emit(groups)

    def abort(self):
        self._abort = True


class PhotoScanWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)
    finished = QtCore.Signal(list)

    def __init__(self, root: str, recurse: bool):
        super().__init__()
        self.root = root
        self.recurse = recurse
        self._abort = False

    @QtCore.Slot()
    def run(self):
        files: List[str] = []
        if self.recurse:
            for r, _, names in os.walk(self.root):
                for n in names:
                    if os.path.splitext(n)[1].lower() in IMAGE_EXTS:
                        files.append(os.path.join(r, n))
        else:
            for n in os.listdir(self.root):
                p = os.path.join(self.root, n)
                if os.path.isfile(p) and os.path.splitext(n)[1].lower() in IMAGE_EXTS:
                    files.append(p)

        total = len(files)
        metas: List[VidMeta] = []
        for i, p in enumerate(files, 1):
            if self._abort: break
            try:
                st = os.stat(p)
                tpath = thumb_cache_path(p)
                if not os.path.exists(tpath):
                    make_image_thumbnail(p, tpath, 480)
                w, h, ph = 0, 0, None
                try:
                    im = Image.open(p).convert("RGB")
                    w, h = im.size
                    ph = imagehash.phash(im)
                except Exception:
                    try:
                        im = Image.open(tpath).convert("RGB")
                        w, h = im.size
                        ph = imagehash.phash(im)
                    except Exception: pass
                vm = VidMeta(p, st.st_size, st.st_mtime, 0.0, w, h, None, ph, tpath if os.path.exists(tpath) else None, 0.0, False)
                vm.quality = calc_quality(vm)
                metas.append(vm)
            except Exception: pass
            self.progress.emit(i, total)

        groups = cluster_images(metas, PHASH_TOL_PHOTO)
        self.finished.emit(groups)

    def abort(self):
        self._abort = True


# ---------- Tabs ----------
class BaseTab(QtWidgets.QWidget):
    worker_cls = None
    is_photo = False
    set_key_last = ""
    recurse_key = ""

    def __init__(self, settings: QtCore.QSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[QtCore.QObject] = None
        self._main_window = parent if isinstance(parent, MainWindow) else None
        self._result_view_mode = "thumbnails"
        # --- LINKER PANEEL: Bibliotheken + Schijven + mapkeuze ---
        left = QtWidgets.QFrame()
        left.setProperty("class", "card")
        left.setMinimumWidth(240)
        left.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Expanding,
        )
        leftl = QtWidgets.QVBoxLayout(left)
        leftl.setContentsMargins(10, 10, 10, 10)
        leftl.setSpacing(8)

        self.fs_model = QtWidgets.QFileSystemModel(self)
        self.fs_model.setRootPath("")
        self.fs_model.setFilter(
            QtCore.QDir.AllDirs
            | QtCore.QDir.NoDotAndDotDot
            | QtCore.QDir.Drives
        )

        lbl_user = QtWidgets.QLabel("Bibliotheken")
        lbl_user.setProperty("class", "sectionTitle")
        self.lbl_user = lbl_user
        leftl.addWidget(lbl_user)

        self.user_list = QtWidgets.QListWidget()
        self.user_list.setIconSize(QtCore.QSize(18, 18))
        self.user_list.setSpacing(2)
        self.user_list.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.user_list.itemClicked.connect(self._on_library_item_selected)
        self.user_list.itemDoubleClicked.connect(self._on_library_item_selected)
        self._populate_pinned_libraries()

        lib_frame = QtWidgets.QFrame()
        lib_frame.setProperty("class", "panel")
        lib_layout = QtWidgets.QVBoxLayout(lib_frame)
        lib_layout.setContentsMargins(6, 6, 6, 6)
        lib_layout.setSpacing(0)
        lib_layout.addWidget(self.user_list)
        leftl.addWidget(lib_frame, 1)

        lbl_drives = QtWidgets.QLabel("Deze PC / Schijven")
        lbl_drives.setProperty("class", "sectionTitle")
        self.lbl_drives = lbl_drives
        leftl.addWidget(lbl_drives)

        self.folder_tree = QtWidgets.QTreeView()
        self.folder_tree.setModel(self.fs_model)
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setRootIndex(self.fs_model.index(""))
        self.folder_tree.setAnimated(True)
        self.folder_tree.setUniformRowHeights(True)
        self.folder_tree.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.folder_tree.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.folder_tree.header().setStretchLastSection(False)
        self.folder_tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        for c in range(1, 4):
            self.folder_tree.hideColumn(c)
        self.folder_tree.selectionModel().selectionChanged.connect(
            self._on_tree_selection_changed
        )
        self.folder_tree.doubleClicked.connect(self._on_tree_double_clicked)

        drive_frame = QtWidgets.QFrame()
        drive_frame.setProperty("class", "panel")
        drive_layout = QtWidgets.QVBoxLayout(drive_frame)
        drive_layout.setContentsMargins(6, 6, 6, 6)
        drive_layout.setSpacing(0)
        drive_layout.addWidget(self.folder_tree)
        leftl.addWidget(drive_frame, 2)

        # Geselecteerde map + browse
        lbl_in = QtWidgets.QLabel("Geselecteerde map")
        lbl_in.setProperty("class", "sectionTitle")
        self.lbl_in = lbl_in
        self.folder_line = DropLineEdit()
        self.folder_line.setPlaceholderText("Drop een map hier of kies links")
        self.folder_line.setMinimumHeight(40)
        browse_btn = QtWidgets.QPushButton("Browse...")
        browse_btn.setFixedWidth(86)
        self.browse_btn = browse_btn
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self.folder_line, 1)
        row.addWidget(browse_btn)
        leftl.addWidget(lbl_in)

        selected_frame = QtWidgets.QFrame()
        selected_frame.setProperty("class", "panel")
        selected_layout = QtWidgets.QVBoxLayout(selected_frame)
        selected_layout.setContentsMargins(6, 6, 6, 6)
        selected_layout.setSpacing(0)
        selected_layout.addLayout(row)
        leftl.addWidget(selected_frame)

        # Opties + status
        self.cb_recurse = QtWidgets.QCheckBox("Submappen meenemen")
        self.cb_recurse.setChecked(True)
        self.remember_cb = QtWidgets.QCheckBox("Onthoud deze map")
        self.remember_cb.setChecked(True)
        self.scan_btn = QtWidgets.QPushButton("Zoeken")
        self.status_lbl = QtWidgets.QLabel("Klaar")
        self.status_lbl.setProperty("class", "hint")

        leftl.addWidget(self.cb_recurse)
        leftl.addWidget(self.remember_cb)
        leftl.addWidget(self.scan_btn)
        leftl.addStretch(1)
        leftl.addWidget(self.status_lbl)

        # --- RECHTER PANEEL: groepen met thumbnails, progress, knoppen ---
        right = QtWidgets.QFrame()
        right.setProperty("class", "card")
        right.setMinimumWidth(420)
        right.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        rightl = QtWidgets.QVBoxLayout(right)
        rightl.setContentsMargins(12, 12, 12, 12)
        rightl.setSpacing(10)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QtWidgets.QWidget()
        self.inner.setObjectName("resultsInner")
        self.vbox = QtWidgets.QVBoxLayout(self.inner)
        self.vbox.addStretch(1)
        self.scroll.setWidget(self.inner)
        self.scroll.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.scroll.customContextMenuRequested.connect(self.open_results_context_menu)
        self.inner.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.inner.customContextMenuRequested.connect(self.open_results_context_menu)

        self.progress = QtWidgets.QProgressBar()

        self.view_mode_combo = QtWidgets.QComboBox()
        self.view_mode_combo.addItem("Miniaturen", "thumbnails")
        self.view_mode_combo.addItem("Lijst details", "details")
        self.view_mode_combo.currentIndexChanged.connect(self.on_view_mode_changed)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.view_mode_combo)
        self.btn_select_all = QtWidgets.QPushButton("Selecteer alles")
        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_select_none = QtWidgets.QPushButton("Deselecteer alles")
        self.btn_select_none.clicked.connect(self.deselect_all)
        self.btn_invert = QtWidgets.QPushButton("Draai selectie om")
        self.btn_invert.clicked.connect(self.invert_selection)
        self.btn_select_others = QtWidgets.QPushButton("Selecteer overige")
        self.btn_select_others.clicked.connect(self.sel_all_except_first)
        self.btn_delete = QtWidgets.QPushButton("Verwijder selectie")
        self.btn_delete.setProperty("class", "danger")
        self.btn_delete.clicked.connect(self.delete_selected_to_trash)
        self.btn_undo = QtWidgets.QPushButton("Maak laatste actie ongedaan")
        self.btn_undo.clicked.connect(self.undo_last_action)
        self.btn_undo.setEnabled(False)

        self.btn_sel_all_except = QtWidgets.QPushButton("Selecteer ALLES behalve 1e")
        self.btn_sel_all_except.clicked.connect(self.sel_all_except_first)

        self.btn_export = QtWidgets.QPushButton("Selectie exporteren naar TXT")
        self.btn_export.clicked.connect(self.export_selection_txt)
        self.btn_export.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))

        self.btn_quick_move = QtWidgets.QPushButton("Snel: verplaats geselecteerde")
        self.btn_quick_move.clicked.connect(self.quick_move_selected)
        self.btn_global_move = QtWidgets.QPushButton("Beste houden per groep")
        self.btn_global_move.clicked.connect(self.global_move_others)

        btn_row.addWidget(self.btn_select_all)
        btn_row.addWidget(self.btn_select_none)
        btn_row.addWidget(self.btn_invert)
        btn_row.addWidget(self.btn_select_others)
        btn_row.addWidget(self.btn_sel_all_except)
        btn_row.addWidget(self.btn_export)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_undo)
        btn_row.addWidget(self.btn_quick_move)
        btn_row.addWidget(self.btn_global_move)

        rightl.addWidget(self.scroll, 1)
        rightl.addWidget(self.progress)
        rightl.addLayout(btn_row)

        # --- Hoofd layout voor tab ---
        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(left)
        self.main_splitter.addWidget(right)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([280, 1120])

        hl = QtWidgets.QVBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(self.main_splitter, 1)

        # Signalen
        browse_btn.clicked.connect(self.pick_folder)
        self.scan_btn.clicked.connect(self.start_scan)

        # Laatste map + recurse-instelling terugzetten
        self.restore_settings()
        self.apply_translations()

    def tr_text(self, key: str, default: str) -> str:
        if self._main_window is not None:
            return self._main_window.tr_text(key, default)
        return default

    def apply_translations(self):
        self.lbl_user.setText(self.tr_text("label_libraries", "Bibliotheken"))
        self.lbl_drives.setText(self.tr_text("label_drives", "Deze PC / Schijven"))
        self.lbl_in.setText(self.tr_text("label_selected_folder", "Geselecteerde map"))
        self.folder_line.setPlaceholderText(
            self.tr_text("placeholder_folder", "Drop een map hier of kies links")
        )
        self.browse_btn.setText(self.tr_text("button_browse", "Browse..."))
        self.cb_recurse.setText(self.tr_text("checkbox_subfolders", "Submappen meenemen"))
        self.remember_cb.setText(self.tr_text("checkbox_remember", "Onthoud deze map"))
        self.scan_btn.setText(self.tr_text("button_scan", "Zoeken"))
        self.btn_select_all.setText(self.tr_text("button_select_all", "Selecteer alles"))
        self.btn_select_none.setText(
            self.tr_text("button_deselect_all", "Deselecteer alles")
        )
        self.btn_invert.setText(
            self.tr_text("button_invert_selection", "Draai selectie om")
        )
        self.btn_select_others.setText(
            self.tr_text("button_select_others", "Selecteer overige")
        )
        self.btn_sel_all_except.setText(
            self.tr_text("button_select_all_except_first", "Selecteer ALLES behalve 1e")
        )
        self.btn_export.setText(
            self.tr_text("button_export_txt", "Selectie exporteren naar TXT")
        )
        self.btn_delete.setText(
            self.tr_text("button_delete_selection", "Verwijder selectie")
        )
        self.btn_undo.setText(self.tr_text("button_undo", "Maak laatste actie ongedaan"))
        self.btn_quick_move.setText(
            self.tr_text("button_quick_move", "Snel: verplaats geselecteerde")
        )
        self.btn_global_move.setText(
            self.tr_text("button_keep_best", "Beste houden per groep")
        )
        self.view_mode_combo.setItemText(0, "Miniaturen")
        self.view_mode_combo.setItemText(1, "Lijst details")


    def restore_settings(self):
        last = self._settings.value(self.set_key_last, "")
        if last and os.path.isdir(last):
            self.folder_line.setText(last)
        recurse_default = self._settings.value(self.recurse_key, True, type=bool)
        self.cb_recurse.setChecked(recurse_default)

    def _populate_pinned_libraries(self):
        self.user_list.clear()
        icon_provider = QtWidgets.QFileIconProvider()
        pinned_locations = [
            ("Documenten", QtCore.QStandardPaths.DocumentsLocation),
            ("Downloads", QtCore.QStandardPaths.DownloadLocation),
            ("Muziek", QtCore.QStandardPaths.MusicLocation),
            ("Afbeeldingen", QtCore.QStandardPaths.PicturesLocation),
            ("Video's", QtCore.QStandardPaths.MoviesLocation),
        ]
        seen_paths = set()
        for label, location_type in pinned_locations:
            locations = QtCore.QStandardPaths.standardLocations(location_type)
            if not locations:
                continue
            path = locations[0]
            if not path or not os.path.isdir(path) or path in seen_paths:
                continue
            seen_paths.add(path)
            item = QtWidgets.QListWidgetItem(
                icon_provider.icon(QtCore.QFileInfo(path)),
                label,
            )
            item.setData(QtCore.Qt.UserRole, path)
            item.setToolTip(path)
            self.user_list.addItem(item)

    def _on_tree_selection_changed(self, sel: QtCore.QItemSelection, desel: QtCore.QItemSelection):
        if not sel.indexes():
            return
        idx = sel.indexes()[0]
        model = idx.model()
        # Alleen QFileSystemModel ondersteunt filePath
        if not hasattr(model, "filePath"):
            return
        path = model.filePath(idx)
        if os.path.isdir(path):
            self.folder_line.setText(path)
        else:
            self.folder_line.setText(os.path.dirname(path))

    def _on_tree_double_clicked(self, idx: QtCore.QModelIndex):
        model = idx.model()
        if not hasattr(model, "filePath"):
            return
        path = model.filePath(idx)
        if os.path.isdir(path):
            self.folder_line.setText(path)
        else:
            self.folder_line.setText(os.path.dirname(path))

    def _on_library_item_selected(self, item: QtWidgets.QListWidgetItem):
        path = item.data(QtCore.Qt.UserRole)
        if not path or not os.path.isdir(path):
            return
        fs_index = self.fs_model.index(path)
        if fs_index.isValid():
            self.folder_tree.setCurrentIndex(fs_index)
            self.folder_tree.scrollTo(fs_index)
        self.folder_line.setText(path)

    def save_recurse_default(self, checked: bool):
        self.cb_recurse.setChecked(checked)
        try:
            self._settings.setValue(self.recurse_key, bool(checked))
        except Exception:
            pass

    def setStatus(self, txt: str):
        self.status_lbl.setText(txt)

    def pick_folder(self):
        dlg = QtWidgets.QFileDialog(self, "Kies een map")
        dlg.setFileMode(QtWidgets.QFileDialog.Directory)
        dlg.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
        if dlg.exec():
            sel = dlg.selectedFiles()
            if sel:
                self.folder_line.setText(sel[0])

    def clear_groups(self):
        while self.vbox.count() > 1:
            it = self.vbox.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def start_scan(self):
        root = self.folder_line.text().strip()
        if not root or not os.path.isdir(root):
            self.setStatus("Kies een geldige map")
            return
        if self.remember_cb.isChecked():
            self._settings.setValue(self.set_key_last, root)

        self.clear_groups()
        self.setStatus(f"Scannen: {root}")
        self.progress.setValue(0)

        if self._thread and self._worker:
            try:
                self._worker.abort()
            except Exception: pass

        self._thread = QtCore.QThread()
        self._worker = self.worker_cls(root, self.cb_recurse.isChecked())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.finished.connect(self.on_done)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @QtCore.Slot(int, int)
    def on_progress(self, cur: int, tot: int):
        self.progress.setMaximum(max(1, tot))
        self.progress.setValue(cur)

    @QtCore.Slot(list)
    def on_done(self, groups: List[List[VidMeta]]):
        label = "fotodubbelen" if self.is_photo else "videodubbelen"
        self.setStatus(f"Gevonden groepen {label}: {len(groups)} (≥2)")
        for g in groups:
            row = GroupRow(g, is_photo=self.is_photo)
            row.set_view_mode(self._result_view_mode)
            self._attach_context_menu(row)
            for card in row.cards:
                self._attach_context_menu(card)
            for detail in row.detail_rows:
                self._attach_context_menu(detail)
            self.vbox.insertWidget(self.vbox.count() - 1, row)
        if not groups:
            QtWidgets.QMessageBox.information(self, "Resultaat", f"Geen {label} gevonden.")

    def _iter_group_rows(self):
        for i in range(self.vbox.count() - 1):
            w = self.vbox.itemAt(i).widget()
            if isinstance(w, GroupRow):
                yield w

    def on_view_mode_changed(self, _index: int):
        self._result_view_mode = self.view_mode_combo.currentData()
        for row in self._iter_group_rows():
            row.set_view_mode(self._result_view_mode)

    def select_all(self):
        for w in self._iter_group_rows():
            for c in w.cards:
                c.chk.setChecked(True)

    def deselect_all(self):
        for w in self._iter_group_rows():
            for c in w.cards:
                c.chk.setChecked(False)

    def invert_selection(self):
        for w in self._iter_group_rows():
            for c in w.cards:
                c.chk.setChecked(not c.chk.isChecked())

    def sel_all_except_first(self):
        for w in self._iter_group_rows():
            for i, c in enumerate(w.cards):
                c.chk.setChecked(i != 0)

    def selected_paths(self) -> List[str]:
        paths: List[str] = []
        for w in self._iter_group_rows():
            paths.extend(w.selected_paths())
        return paths

    def export_selection_txt(self):
        lines = []
        count = 0
        for w in self._iter_group_rows():
            for c in w.cards:
                if c.chk.isChecked():
                    lines.append(c.vm.path)
                    count += 1
        
        if not lines:
            QtWidgets.QMessageBox.information(self, "Export", "Niets aangevinkt om te exporteren.")
            return

        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Lijst opslaan", "", "Text (*.txt)")
        if fn:
            try:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                QtWidgets.QMessageBox.information(self, "Succes", f"{count} paden opgeslagen in:\n{fn}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Fout", f"Kon bestand niet opslaan:\n{e}")

    def delete_selected_to_trash(self):
        paths = self.selected_paths()
        if not paths:
            QtWidgets.QMessageBox.information(self, "Verwijderen", "Er is niets geselecteerd.")
            return

        kind = "media-bestand" if len(paths) == 1 else "media-bestanden"
        reply = QtWidgets.QMessageBox.question(
            self,
            "Bevestig verwijderen",
            (
                f"Weet je zeker dat je {len(paths)} {kind} wilt verplaatsen "
                "naar de prullenbak?"
            ),
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        moved = 0
        errors: List[str] = []
        for path in paths:
            try:
                move_to_recycle_bin(path)
                moved += 1
            except Exception as e:
                errors.append(f"{path}: {e}")

        message = f"{moved} media-bestand(en) verplaatst naar de prullenbak."
        if errors:
            message += f"\n\n{len(errors)} bestand(en) gaven een fout."
        QtWidgets.QMessageBox.information(self, "Verwijderen", message)
        self.start_scan()

    def undo_last_action(self):
        QtWidgets.QMessageBox.information(
            self,
            "Ongedaan maken",
            "Prullenbakacties kunnen niet vanuit deze app ongedaan worden gemaakt.",
        )

    def open_results_context_menu(self, pos: QtCore.QPoint):
        menu = QtWidgets.QMenu(self)
        act_view_thumbs = menu.addAction("Weergave: Miniaturen")
        act_view_details = menu.addAction("Weergave: Lijst details")
        menu.addSeparator()
        act_select_all = menu.addAction("Selecteer alles")
        act_select_none = menu.addAction("Deselecteer alles")
        act_invert = menu.addAction("Draai selectie om")
        act_select_others = menu.addAction("Selecteer overige")
        menu.addSeparator()
        act_export = menu.addAction("Selectie exporteren naar TXT")
        act_quick_move = menu.addAction("Snel: verplaats geselecteerde")
        act_keep_best = menu.addAction("Beste houden per groep")
        menu.addSeparator()
        act_delete = menu.addAction("Verwijder selectie")
        act_undo = menu.addAction("Maak laatste actie ongedaan")
        act_undo.setEnabled(False)

        chosen = menu.exec(self.scroll.viewport().mapToGlobal(pos))
        if chosen == act_view_thumbs:
            self.view_mode_combo.setCurrentIndex(0)
        elif chosen == act_view_details:
            self.view_mode_combo.setCurrentIndex(1)
        elif chosen == act_select_all:
            self.select_all()
        elif chosen == act_select_none:
            self.deselect_all()
        elif chosen == act_invert:
            self.invert_selection()
        elif chosen == act_select_others:
            self.sel_all_except_first()
        elif chosen == act_export:
            self.export_selection_txt()
        elif chosen == act_quick_move:
            self.quick_move_selected()
        elif chosen == act_keep_best:
            self.global_move_others()
        elif chosen == act_delete:
            self.delete_selected_to_trash()
        elif chosen == act_undo:
            self.undo_last_action()

    def _attach_context_menu(self, widget: QtWidgets.QWidget):
        widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda local_pos, source=widget: self.open_results_context_menu(
                self.scroll.viewport().mapFromGlobal(source.mapToGlobal(local_pos))
            )
        )

    def quick_move_selected(self):
        base = self.folder_line.text().strip()
        if not base or not os.path.isdir(base):
            QtWidgets.QMessageBox.warning(self, "Fout", "Geen geldige bronmap.")
            return
        suffix = "Duplicate moved (foto)" if self.is_photo else "Duplicate moved (video)"
        dest = os.path.join(base, suffix)
        os.makedirs(dest, exist_ok=True)
        moved = 0
        for p in self.selected_paths():
            try:
                shutil.move(p, os.path.join(dest, os.path.basename(p)))
                moved += 1
            except Exception as e:
                print("Move fail:", p, e)
        QtWidgets.QMessageBox.information(self, "Klaar", f"{moved} bestand(en) verplaatst → {dest}")
        self.start_scan()

    def global_move_others(self):
        dest = QtWidgets.QFileDialog.getExistingDirectory(self, "Kies doelmap")
        if not dest: return
        suffix = "origineel_foto" if self.is_photo else "origineel_video"
        keep_dir = os.path.join(dest, suffix)
        os.makedirs(dest, exist_ok=True)
        os.makedirs(keep_dir, exist_ok=True)
        moved, groups = 0, 0
        for w in self._iter_group_rows():
            if not w.items: continue
            groups += 1
            best = w.items[0].path
            for c in w.cards:
                p = c.vm.path
                try:
                    if p == best:
                        shutil.move(p, os.path.join(keep_dir, os.path.basename(p)))
                    else:
                        shutil.move(p, os.path.join(dest, os.path.basename(p)))
                    moved += 1
                except Exception as e:
                    print("Move fail:", p, e)
        QtWidgets.QMessageBox.information(self, "Klaar", f"{moved} bestand(en) verplaatst uit {groups} groep(en).\nDoel: {dest}\nOrigineel: {keep_dir}")
        self.start_scan()

    def abort_worker(self):
        try:
            if self._worker and self._thread and self._thread.isRunning():
                self._worker.abort()
                self._thread.quit()
                self._thread.wait(1500)
        except Exception: pass


class VideoTab(BaseTab):
    worker_cls = VideoScanWorker
    is_photo = False
    set_key_last = SET_KEY_LAST_VIDEO
    recurse_key = "recurse_default_video"


class PhotoTab(BaseTab):
    worker_cls = PhotoScanWorker
    is_photo = True
    set_key_last = SET_KEY_LAST_PHOTO
    recurse_key = "recurse_default_photo"


# ---------- Main window ----------


class MainWindow(QtWidgets.QMainWindow):
    def _update_header_icon(self):
        if not hasattr(self, "header_icon"):
            return
        header_pixmap = QtGui.QPixmap(resource_path("logo_flat.png"))
        if header_pixmap.isNull():
            self.header_icon.clear()
            return
        target_h = max(32, self.header.height() - 12)
        scaled = header_pixmap.scaledToHeight(
            target_h,
            QtCore.Qt.SmoothTransformation,
        )
        self.header_icon.setPixmap(scaled)
        self.header_icon.setFixedSize(scaled.size())

    def __init__(self):
        super().__init__()
        QtCore.QCoreApplication.setOrganizationName(ORG)
        QtCore.QCoreApplication.setApplicationName(APP_SETTINGS_NAME)
        self._icon_path = resource_path("icon.ico")
        self._background_path = resource_path("BG.png")

        self.setWindowTitle(APP_NAME)
        self.resize(1400, 820)
        self.setMinimumSize(960, 620)
        if os.path.exists(self._icon_path):
            self.setWindowIcon(QtGui.QIcon(self._icon_path))
        self._settings = QtCore.QSettings(ORG, APP_SETTINGS_NAME)
        self._language_options = load_language_options()
        self._language_actions: Dict[str, QtGui.QAction] = {}
        self._translations = dict(DEFAULT_TRANSLATIONS)
        self._current_language_code = self._settings.value(SET_KEY_LANGUAGE, "en", type=str)

        mb = self.menuBar()
        m_file = mb.addMenu("Bestand")
        self.m_file = m_file
        act_exit = QtGui.QAction("Afsluiten", self)
        self.act_exit = act_exit
        act_exit.triggered.connect(self.close)
        m_file.addAction(act_exit)

        m_settings = mb.addMenu("Instellingen")
        self.m_settings = m_settings
        self.act_recurse_video = QtGui.QAction("Video: submappen standaard meenemen", self)
        self.act_recurse_video.setCheckable(True)
        self.act_recurse_photo = QtGui.QAction("Foto: submappen standaard meenemen", self)
        self.act_recurse_photo.setCheckable(True)
        self.act_play_intro = QtGui.QAction("Intro afspelen bij opstarten", self)
        self.act_play_intro.setCheckable(True)
        m_settings.addAction(self.act_recurse_video)
        m_settings.addAction(self.act_recurse_photo)
        m_settings.addAction(self.act_play_intro)
        m_settings.addSeparator()
        self.language_menu = m_settings.addMenu("Taal")
        self.language_group = QtGui.QActionGroup(self)
        self.language_group.setExclusive(True)
        for language in self._language_options:
            action = QtGui.QAction(language["label"], self)
            action.setCheckable(True)
            action.setData(language["code"])
            action.triggered.connect(
                lambda checked=False, code=language["code"]: self.set_ui_language(code)
            )
            self.language_group.addAction(action)
            self.language_menu.addAction(action)
            self._language_actions[language["code"]] = action

        m_help = mb.addMenu("Help")
        self.m_help = m_help
        act_about = QtGui.QAction("Info / Over", self)
        self.act_about = act_about
        act_about.triggered.connect(self.show_about_video_dialog)
        m_help.addAction(act_about)
        act_scripts = QtGui.QAction("Scripts en modules", self)
        self.act_scripts = act_scripts
        act_scripts.triggered.connect(self.show_scripts_dialog)
        m_help.addAction(act_scripts)

        header = QtWidgets.QFrame()
        header.setMinimumHeight(64)
        header.setMaximumHeight(110)
        header.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed,
        )
        header.setStyleSheet(
            "background: #111827;"
            "border: none;"
        )
        self.header = header
        hhl = QtWidgets.QHBoxLayout(header)
        hhl.setContentsMargins(18, 6, 18, 6)
        hhl.setSpacing(16)

        self.header_icon = QtWidgets.QLabel()
        self.header_icon.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hhl.addWidget(self.header_icon, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.title = QtWidgets.QLabel(APP_NAME)
        self.title.setStyleSheet(
            "color: #f2f7ff;"
            "font-family: 'Aptos', 'Segoe UI', 'Arial', sans-serif;"
            "font-size: 29px;"
            "font-weight: 400;"
            "letter-spacing: 0px;"
            "background: transparent;"
        )
        self.title.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hhl.addWidget(self.title, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hhl.addStretch(1)
        self._update_header_icon()

        self.tabs = QtWidgets.QTabWidget()
        self.video_tab = VideoTab(self._settings, self)
        self.photo_tab = PhotoTab(self._settings, self)
        self.tabs.addTab(self.video_tab, "Video-dubbelen")
        self.tabs.addTab(self.photo_tab, "Foto-dubbelen")

        footer = QtWidgets.QFrame()
        footer.setMinimumHeight(28)
        footer.setMaximumHeight(40)
        footer.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Fixed,
        )
        footer.setStyleSheet("background:#101722;border-top:1px solid #0d1421;")
        fl = QtWidgets.QHBoxLayout(footer)
        fl.setContentsMargins(12, 0, 12, 0)
        self.footer_lbl = QtWidgets.QLabel("Klaar")
        self.footer_lbl.setStyleSheet("color:#7FAED6")
        fl.addWidget(self.footer_lbl)
        fl.addStretch(1)

        central = WatermarkWidget(self._background_path)
        v = QtWidgets.QVBoxLayout(central)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(8)
        v.addWidget(header)
        v.addWidget(self.tabs, 1)
        v.addWidget(footer)
        self.setCentralWidget(central)

        self.act_recurse_video.setChecked(self._settings.value("recurse_default_video", True, type=bool))
        self.act_recurse_photo.setChecked(self._settings.value("recurse_default_photo", True, type=bool))
        self.act_play_intro.setChecked(self._settings.value(SET_KEY_PLAY_INTRO, True, type=bool))
        self.act_recurse_video.toggled.connect(self.video_tab.save_recurse_default)
        self.act_recurse_photo.toggled.connect(self.photo_tab.save_recurse_default)
        self.act_play_intro.toggled.connect(
            lambda checked: self._settings.setValue(SET_KEY_PLAY_INTRO, bool(checked))
        )
        self.set_ui_language(self._current_language_code, persist=False)

        self.setStyleSheet(DarkPalette.stylesheet())
        geom = self._settings.value("main/geometry")
        if geom is not None: self.restoreGeometry(geom)
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_header_icon()

    def on_tab_changed(self, idx: int):
        base = self.tr_text("tab_video", "Video-dubbelen") if idx == 0 else self.tr_text("tab_photo", "Foto-dubbelen")
        self.footer_lbl.setText(
            f"{base} | {self.tr_text('footer_language', 'Taal')}: {self.current_language_label()}"
        )

    def tr_text(self, key: str, default: str) -> str:
        return self._translations.get(key, default)

    def current_language_label(self) -> str:
        for language in self._language_options:
            if language["code"] == self._current_language_code:
                return language["label"]
        return self._current_language_code

    def set_ui_language(self, code: str, persist: bool = True):
        available_codes = {language["code"] for language in self._language_options}
        if code not in available_codes:
            code = "en" if "en" in available_codes else self._language_options[0]["code"]
        self._current_language_code = code
        self._translations = load_translations(code)
        for action_code, action in self._language_actions.items():
            action.setChecked(action_code == code)
        if persist:
            self._settings.setValue(SET_KEY_LANGUAGE, code)
        self.m_file.setTitle(self.tr_text("menu_file", "Bestand"))
        self.m_settings.setTitle(self.tr_text("menu_settings", "Instellingen"))
        self.m_help.setTitle(self.tr_text("menu_help", "Help"))
        self.language_menu.setTitle(self.tr_text("menu_language", "Taal"))
        self.act_exit.setText(self.tr_text("action_exit", "Afsluiten"))
        self.act_about.setText(self.tr_text("action_about", "Info / Over"))
        self.act_scripts.setText(self.tr_text("action_scripts", "Scripts en modules"))
        self.act_recurse_video.setText(
            self.tr_text("action_recurse_video", "Video: submappen standaard meenemen")
        )
        self.act_recurse_photo.setText(
            self.tr_text("action_recurse_photo", "Foto: submappen standaard meenemen")
        )
        self.act_play_intro.setText(
            self.tr_text("action_play_intro", "Intro afspelen bij opstarten")
        )
        self.tabs.setTabText(0, self.tr_text("tab_video", "Video-dubbelen"))
        self.tabs.setTabText(1, self.tr_text("tab_photo", "Foto-dubbelen"))
        self.video_tab.apply_translations()
        self.photo_tab.apply_translations()
        self.on_tab_changed(self.tabs.currentIndex() if hasattr(self, "tabs") else 0)

    def show_scripts_dialog(self):
        text = (
            f"{self.tr_text('scripts_main', 'Hoofdscript')}:\n"
            "  MediaDuplicatieFinder.py\n\n"
            f"{self.tr_text('scripts_modules', 'Modules')}:\n"
            "  PySide6, Pillow, imagehash, numpy\n\n"
            f"{self.tr_text('scripts_tools', 'Tools')}:\n"
            "  ffmpeg, ffprobe\n\n"
            f"{self.tr_text('scripts_github', 'GitHub')}:\n"
            "  RymndA"
        )
        QtWidgets.QMessageBox.information(
            self,
            self.tr_text("scripts_title", "Scripts en modules"),
            text,
        )

    def show_about_video_dialog(self):
        left_text = (
            "Media audit for video and photo duplicates.\n"
            "Export and recycle bin support available.\n\n"
            f"Selected language:\n{self.current_language_label()}"
        )
        right_text = (
            "Author / GitHub:\n"
            "RymndA\n\n"
            "Release:\n"
            "2026-April"
        )
        dialog = AboutVideoDialog(
            resource_path("Intro_about.mp4"),
            self._icon_path,
            APP_NAME,
            left_text,
            right_text,
            self,
        )
        dialog.exec()

    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        try:
            self.video_tab.abort_worker()
            self.photo_tab.abort_worker()
        except Exception: pass
        try:
            self._settings.setValue("main/geometry", self.saveGeometry())
        except Exception: pass
        super().closeEvent(e)


def main():
    QtCore.QCoreApplication.setOrganizationName(ORG)
    QtCore.QCoreApplication.setApplicationName(APP_SETTINGS_NAME)
    app = QtWidgets.QApplication(sys.argv)
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QtGui.QIcon(icon_path))

    settings = QtCore.QSettings(ORG, APP_SETTINGS_NAME)
    intro_path = resource_path("intro.mp4")
    if settings.value(SET_KEY_PLAY_INTRO, True, type=bool) and os.path.exists(intro_path):
        intro = IntroDialog(intro_path, icon_path)
        intro.exec()

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
