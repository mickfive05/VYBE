"""Command-line interface and global shortcut listener."""
from __future__ import annotations

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import sys
import threading

from . import __version__
from .core import VybeError, data_dir, download, exclusive, requirements, settings, youtube_url

LOG = logging.getLogger("vybe")


def clipboard_url() -> str:
    try:
        import pyperclip
        return youtube_url(pyperclip.paste())
    except VybeError:
        raise
    except Exception as exc:
        raise VybeError(f"Cannot read clipboard: {exc}. See docs/INSTALL.md.") from exc


def listen(config: dict, stop: threading.Event) -> None:
    if sys.platform.startswith("linux") and os.environ.get("XDG_SESSION_TYPE") == "wayland":
        raise VybeError("Wayland: bind 'vybe download mp4' and 'vybe download mp3' in desktop settings.")
    try:
        from pynput import keyboard
    except Exception as exc:
        raise VybeError(f"Cannot start global shortcuts: {exc}. Check desktop permissions.") from exc
    keys = [config["mp4_hotkey"], config["mp3_hotkey"]]
    try:
        parsed = [frozenset(keyboard.HotKey.parse(key)) for key in keys]
        if any(not key for key in parsed) or parsed[0] == parsed[1]:
            raise ValueError("Use two distinct, nonempty shortcuts")
    except ValueError as exc:
        raise VybeError(f"Invalid shortcuts: {exc}") from exc

    busy = threading.Lock()
    workers: list[threading.Thread] = []

    def trigger(mode: str) -> None:
        # Never perform clipboard I/O or downloading on the OS keyboard callback.
        if stop.is_set() or not busy.acquire(blocking=False):
            return

        def work() -> None:
            try:
                url = clipboard_url()
                LOG.info("Starting %s download", mode)
                download(url, mode, Path(config["output"]), stop)
                LOG.info("%s download completed in %s", mode, config["output"])
            except (VybeError, OSError) as exc:
                LOG.error("%s", exc)
            finally:
                busy.release()

        workers[:] = [worker for worker in workers if worker.is_alive()]
        worker = threading.Thread(target=work, name="vybe-download")
        workers.append(worker)
        worker.start()

    with exclusive(data_dir() / "listener.lock"):
        listener = keyboard.GlobalHotKeys({keys[0]: lambda: trigger("mp4"),
                                          keys[1]: lambda: trigger("mp3")})
        if getattr(listener, "IS_TRUSTED", True) is False:
            raise VybeError("Grant Accessibility/Input Monitoring to your terminal or Python, then restart.")
        listener.start()
        try:
            listener.wait()
            LOG.info("Ready: MP4 %s | MP3 %s | output %s", *keys, config["output"])
            while not stop.wait(0.25):
                if not listener.is_alive():
                    listener.join()  # Propagate callback/backend failures.
                    raise VybeError("Keyboard listener stopped unexpectedly")
        finally:
            stop.set()
            listener.stop()
            listener.join(timeout=2)
            for worker in workers:
                worker.join()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VYBE — copy a YouTube link, keep the moment.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", type=Path, help="JSON configuration file")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("run", help="Listen for MP4 and MP3 global shortcuts")
    sub.add_parser("doctor", help="Check dependencies and clipboard access")
    get = sub.add_parser("download", help="Download once; reads clipboard unless --url is provided")
    get.add_argument("format", choices=["mp4", "mp3"])
    get.add_argument("--url", help="Explicit YouTube video URL")
    get.add_argument("--output", type=Path, help="Override output directory")
    args = parser.parse_args(argv)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        config = settings(args.config)
        data_dir().mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(data_dir() / "vybe.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOG.setLevel(logging.INFO)
        LOG.handlers.clear()
        LOG.addHandler(handler)
        LOG.addHandler(logging.StreamHandler())
        requirements()
        if args.action == "doctor":
            import pyperclip
            pyperclip.paste()  # Never print clipboard contents.
            print(f"Dependencies and clipboard OK. Output: {config['output']}")
            print(f"Logs: {data_dir() / 'vybe.log'}")
            print("Global shortcut permissions must still be checked with 'vybe run'.")
        elif args.action == "download":
            output = (args.output or Path(config["output"])).expanduser().resolve()
            download(args.url if args.url is not None else clipboard_url(), args.format, output, stop)
            LOG.info("Download completed in %s", output)
        else:
            listen(config, stop)
        return 0
    except (VybeError, OSError, ImportError) as exc:
        print(f"VYBE: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        LOG.exception("Unexpected failure")
        print(f"VYBE: {exc}", file=sys.stderr)
        return 1
    finally:
        for handler in LOG.handlers[:]:
            handler.close()
            LOG.removeHandler(handler)


if __name__ == "__main__":
    raise SystemExit(main())
