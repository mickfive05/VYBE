# Reproduce the media demo

The README animation is a rendered replay of actual test output. It is not a
screen recording and does not show physical shortcuts or a YouTube download.
The test creates one second of synthetic H.264/AAC video and runs the real
yt-dlp transfer and FFmpeg conversion over a loopback HTTP connection.

Use the project's virtual environment and install the development-only Pillow
renderer plus FFmpeg (or the optional imageio-ffmpeg test helper). No third-party
video is used, and no changes to your desktop clipboard are required.

```sh
python -m pip install -e .
python -m pip install Pillow imageio-ffmpeg
python scripts/record_demo.py
```

The script fails if the media test fails. On success it writes `assets/demo.gif`,
`assets/demo-transcript.txt`, and `assets/social-preview.png`. It renders only
the deliberately emitted demo milestones, removing temporary paths from the
presentation. All decoding assertions must pass before a success milestone
is emitted. System requirements and URL validation are substituted for this
local fixture, as documented in the test and verification record.

If Pillow and VYBE are installed in different Python environments, run the
renderer with its Python and pass `--python /absolute/path/to/VYBE/python`
to select the interpreter for the media test.
