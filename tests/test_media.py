"""Opt-in offline media test: VYBE_MEDIA_TESTS=1; requires FFmpeg.

Uses synthetic content served on loopback, not YouTube. imageio-ffmpeg can
provide a test-only FFmpeg binary when no system installation exists.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from vybe.core import download


@unittest.skipUnless(os.environ.get("VYBE_MEDIA_TESTS") == "1", "opt-in real media test")
class MediaTests(unittest.TestCase):
    def test_real_downloader_and_ffmpeg_for_both_formats(self):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bindir = root / "bin"
            bindir.mkdir()
            executable = bindir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            shutil.copy2(ffmpeg, executable)
            subprocess.run([str(executable), "-v", "error", "-f", "lavfi", "-i",
                            "color=c=blue:s=160x90:r=10", "-f", "lavfi", "-i",
                            "sine=frequency=440:sample_rate=44100", "-t", "1",
                            "-c:v", "libx264", "-c:a", "aac", str(root / "fixture.mp4")], check=True)
            print("VYBE DEMO | Created a 1-second synthetic H.264/AAC fixture.", flush=True)
            handler = partial(SimpleHTTPRequestHandler, directory=str(root))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/fixture.mp4"
                envpath = str(bindir) + os.pathsep + os.environ.get("PATH", "")
                # Isolate site validation/dependency preflight: this exercises the
                # real yt-dlp command, transfer, conversion, and output verification.
                with patch("vybe.core.youtube_url", side_effect=lambda value: value), \
                        patch("vybe.core.requirements"), \
                        patch("vybe.core.data_dir", return_value=root / "state"), \
                        patch.dict(os.environ, {"PATH": envpath}):
                    for mode in ("mp4", "mp3"):
                        output = root / mode
                        download(url, mode, output, threading.Event())
                        files = list(output.glob(f"*.{mode}"))
                        self.assertEqual(len(files), 1)
                        result = subprocess.run([str(executable), "-i", str(files[0]),
                                                 "-f", "null", "-"], capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn("Audio:", result.stderr)
                        if mode == "mp4":
                            self.assertIn("Video:", result.stderr)
                        else:
                            self.assertIn("Audio: mp3", result.stderr)
                        print(f"VYBE DEMO | {mode.upper()} saved and decoded successfully: {files[0].name}", flush=True)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
