import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from vybe.core import VybeError, command, download, exclusive, settings, youtube_url

ID = "BaW_jenozKc"
URL = f"https://www.youtube.com/watch?v={ID}"


class CoreTests(unittest.TestCase):
    def test_supported_urls_normalize_and_drop_playlist(self):
        for text in [f" https://youtu.be/{ID}?t=2 \n", URL + "&list=PLtest",
                     f"https://m.youtube.com/shorts/{ID}", f"https://youtube.com/live/{ID}",
                     f"https://music.youtube.com/watch?v={ID}", f"https://youtube.com/embed/{ID}"]:
            with self.subTest(text=text):
                self.assertEqual(youtube_url(text), URL)

    def test_reject_ambiguous_or_untrusted_clipboard(self):
        for text in ["", ID, "file:///tmp/video", "--exec=bad", URL + " " + URL,
                     URL.replace("www.youtube.com", "www.youtube.com.evil.test"),
                     URL.replace("www.youtube.com", "user@www.youtube.com"),
                     URL + "&v=" + ID, "https://youtube.com/playlist?list=test",
                     "https://youtu.be/not-an-id", "https://youtu.be:443/" + ID]:
            with self.subTest(text=text), self.assertRaises(VybeError):
                youtube_url(text)

    def test_format_arguments_are_isolated(self):
        args = command(URL, "mp4", Path("some folder"))
        self.assertEqual(args[-2:], ["--", URL])
        self.assertIn("--ignore-config", args)
        self.assertIn("--no-playlist", args)
        self.assertIn("--no-overwrites", args)
        self.assertIn("--remux-video", args)
        audio = command(URL, "mp3", Path("some folder"))
        self.assertIn("--extract-audio", audio)
        self.assertEqual(audio[audio.index("--audio-format") + 1], "mp3")
        with self.assertRaises(VybeError):
            command(URL, "exe", Path("."))

    def test_config_defaults_overrides_and_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            self.assertEqual(settings(path)["mp4_hotkey"], "<ctrl>+<alt>+v")
            path.write_text(json.dumps({"output": temp, "mp3_hotkey": "<ctrl>+a"}))
            self.assertEqual(settings(path)["output"], str(Path(temp).resolve()))
            for value in ["{", '[]', '{"unknown":true}', '{"output":4}', '{"output":""}']:
                path.write_text(value)
                with self.assertRaises(VybeError):
                    settings(path)

    def test_lock_excludes_and_releases(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lock"
            with exclusive(path):
                with self.assertRaises(VybeError):
                    with exclusive(path):
                        self.fail("second lock acquired")
            with exclusive(path):
                pass

    def test_download_reports_success_only_for_real_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "video.mp3"
            output.write_bytes(b"audio")

            def process(args, **kwargs):
                report = Path(args[args.index("--print-to-file") + 2])
                report.write_text(str(output) + "\n", encoding="utf-8")
                proc = unittest.mock.MagicMock()
                proc.__enter__.return_value = proc
                proc.poll.return_value = 0
                proc.returncode = 0
                return proc

            with patch("vybe.core.requirements"), patch("vybe.core.data_dir", return_value=root), \
                    patch("vybe.core.subprocess.Popen", side_effect=process):
                download(URL, "mp3", root, threading.Event())
                with self.assertRaisesRegex(VybeError, "verified output"):
                    download(URL, "mp4", root, threading.Event())

    def test_process_failure_and_cancellation(self):
        with tempfile.TemporaryDirectory() as temp:
            proc = unittest.mock.MagicMock()
            proc.__enter__.return_value = proc
            with patch("vybe.core.requirements"), patch("vybe.core.data_dir", return_value=Path(temp)), \
                    patch("vybe.core.subprocess.Popen", return_value=proc):
                proc.poll.return_value = 1
                proc.returncode = 1
                with self.assertRaisesRegex(VybeError, "exit 1"):
                    download(URL, "mp3", Path(temp), threading.Event())
                proc.poll.return_value = None
                stop = threading.Event()
                stop.set()
                with self.assertRaisesRegex(VybeError, "cancelled"):
                    download(URL, "mp3", Path(temp), stop)
                proc.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
