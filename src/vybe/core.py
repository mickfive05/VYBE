"""Download policy and process management; no desktop imports at module load."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import tempfile
from urllib.parse import parse_qs, urlsplit


class VybeError(Exception):
    """An actionable user-facing failure."""


def data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "VYBE"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/VYBE"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "vybe"


def youtube_url(text: str) -> str:
    """Accept exactly one supported video URL, stripping playlist/tracking data."""
    try:
        url = urlsplit(text.strip())
        if url.scheme not in ("http", "https") or url.username or url.password or url.port:
            raise ValueError
        host = url.hostname
        parts = url.path.strip("/").split("/")
        if host == "youtu.be" and len(parts) == 1:
            video_id = parts[0]
        elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
            if url.path == "/watch":
                ids = parse_qs(url.query).get("v", [])
                if len(ids) != 1:
                    raise ValueError
                video_id = ids[0]
            elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
                video_id = parts[1]
            else:
                raise ValueError
        else:
            raise ValueError
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError
    except (ValueError, AttributeError):
        raise VybeError("Copy one YouTube video URL (watch, Shorts, live, or youtu.be).") from None
    return f"https://www.youtube.com/watch?v={video_id}"


def settings(path: Path | None = None) -> dict:
    result = {"output": str(Path.home() / "Downloads/VYBE"),
              "mp4_hotkey": "<ctrl>+<alt>+v", "mp3_hotkey": "<ctrl>+<alt>+a"}
    path = path or data_dir() / "config.json"
    if path.exists():
        try:
            custom = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(custom, dict) or set(custom) - set(result):
                raise ValueError("Expected an object with output, mp4_hotkey, mp3_hotkey only")
            if any(not isinstance(v, str) or not v.strip() for v in custom.values()):
                raise ValueError("All settings must be nonempty strings")
            result.update(custom)
        except (ValueError, OSError) as exc:
            raise VybeError(f"Invalid config {path}: {exc}") from exc
    result["output"] = str(Path(result["output"]).expanduser().resolve())
    return result


def requirements() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe", "deno") if not shutil.which(name)]
    if missing:
        raise VybeError("Install and add to PATH: " + ", ".join(missing) + ". See docs/INSTALL.md.")
    import importlib.util
    if importlib.util.find_spec("yt_dlp") is None:
        raise VybeError("Install VYBE dependencies with python -m pip install .")


def command(url: str, mode: str, output: Path) -> list[str]:
    if mode not in {"mp4", "mp3"}:
        raise VybeError("Format must be mp4 or mp3")
    args = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-plugin-dirs",
            "--no-playlist", "--no-overwrites", "--no-progress", "--newline",
            "--socket-timeout", "30", "--retries", "3", "--windows-filenames",
            "--paths", str(output), "--output", "%(title).160B [%(id)s].%(ext)s",
            "--print", "after_move:filepath"]
    if mode == "mp4":
        args += ["--format", "bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
                 "--merge-output-format", "mp4", "--remux-video", "mp4"]
    else:
        args += ["--format", "bestaudio/best", "--extract-audio", "--audio-format", "mp3",
                 "--audio-quality", "0"]
    return args + ["--", youtube_url(url)]


@contextlib.contextmanager
def exclusive(path: Path):
    """OS-held lock: automatically released on exit or crash, including Windows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        try:
            # A Windows byte-range lock can reject this initial read too.
            # Treat that contention exactly like a failed lock acquisition.
            handle.seek(0)
            if not handle.read(1):
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise VybeError("Another VYBE instance or download is already running.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def download(url: str, mode: str, output: Path, stop: threading.Event) -> None:
    args = command(url, mode, output)
    requirements()
    output.mkdir(parents=True, exist_ok=True)
    with exclusive(data_dir() / "download.lock"), tempfile.TemporaryDirectory(prefix="vybe-") as temp:
        report = Path(temp) / "completed.txt"
        args[-2:-2] = ["--print-to-file", "after_move:filepath", str(report)]
        # Inherit output so yt-dlp diagnostics reach the CLI or the rotating log.
        with subprocess.Popen(args, creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)) as proc:
            try:
                while proc.poll() is None:
                    if stop.wait(0.2):
                        raise VybeError("Download cancelled; partial files may be resumed on retry.")
                if proc.returncode:
                    raise VybeError(f"yt-dlp failed (exit {proc.returncode}); inspect its diagnostics above.")
                paths = report.read_text(encoding="utf-8").splitlines() if report.exists() else []
                if not paths or any(not Path(p).is_file() or Path(p).suffix.lower() != f".{mode}"
                                    or Path(p).stat().st_size == 0 for p in paths):
                    raise VybeError("yt-dlp exited without a verified output file; inspect its diagnostics.")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
