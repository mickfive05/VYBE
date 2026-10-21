import io
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vybe import cli
from vybe.core import VybeError


class CLITests(unittest.TestCase):
    def test_clipboard_failure_is_actionable(self):
        with patch.dict("sys.modules", {"pyperclip": SimpleNamespace(paste=lambda: (_ for _ in ()).throw(RuntimeError("no backend")))}):
            with self.assertRaisesRegex(VybeError, "Cannot read clipboard"):
                cli.clipboard_url()

    def test_wayland_routes_to_native_shortcuts(self):
        with patch.object(cli, "sys", SimpleNamespace(platform="linux")), patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with self.assertRaisesRegex(VybeError, "bind 'vybe download mp4'"):
                cli.listen({}, threading.Event())

    def test_untrusted_listener_fails_before_start(self):
        class Listener:
            IS_TRUSTED = False

            def __init__(self, callbacks):
                pass

        keyboard = SimpleNamespace(HotKey=SimpleNamespace(parse=lambda key: list(key)), GlobalHotKeys=Listener)
        with tempfile.TemporaryDirectory() as temp, \
                patch.dict("sys.modules", {"pynput": SimpleNamespace(keyboard=keyboard)}), \
                patch.object(cli, "data_dir", return_value=Path(temp)), \
                patch.object(cli, "sys", SimpleNamespace(platform="darwin")):
            with self.assertRaisesRegex(VybeError, "Grant Accessibility"):
                cli.listen({"mp4_hotkey": "v", "mp3_hotkey": "a"}, threading.Event())

    def test_both_callbacks_dispatch_requested_formats(self):
        for mode, key in [("mp4", "v"), ("mp3", "a")]:
            stop = threading.Event()
            calls = []

            class Listener:
                IS_TRUSTED = True

                def __init__(self, callbacks):
                    self.callbacks = callbacks

                def start(self):
                    self.callbacks[key]()

                def wait(self):
                    pass

                def stop(self):
                    pass

                def join(self, timeout=None):
                    pass

                def is_alive(self):
                    return True

            def downloaded(url, requested, output, event):
                calls.append((url, requested))
                event.set()

            keyboard = SimpleNamespace(HotKey=SimpleNamespace(parse=lambda text: list(text)), GlobalHotKeys=Listener)
            with tempfile.TemporaryDirectory() as temp, \
                    patch.dict("sys.modules", {"pynput": SimpleNamespace(keyboard=keyboard)}), \
                    patch.object(cli, "sys", SimpleNamespace(platform="darwin")), \
                    patch.object(cli, "data_dir", return_value=Path(temp)), \
                    patch.object(cli, "clipboard_url", return_value="https://youtu.be/BaW_jenozKc"), \
                    patch.object(cli, "download", side_effect=downloaded):
                cli.listen({"mp4_hotkey": "v", "mp3_hotkey": "a", "output": temp}, stop)
            self.assertEqual(calls, [("https://youtu.be/BaW_jenozKc", mode)])

    def test_doctor_failure_returns_nonzero_without_reading_clipboard(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(cli, "data_dir", return_value=Path(temp)), \
                patch.object(cli, "settings", return_value={}), \
                patch.object(cli, "requirements", side_effect=VybeError("Missing ffmpeg")), \
                patch.object(cli, "clipboard_url") as clipboard, \
                patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(cli.main(["doctor"]), 1)
            self.assertIn("Missing ffmpeg", stderr.getvalue())
            clipboard.assert_not_called()
