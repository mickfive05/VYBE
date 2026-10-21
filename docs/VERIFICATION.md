# Verification record

Checked on 21 October 2026 in macOS ARM64 with CPython 3.12.14.

## Completed locally

- Installed the project and its real Python dependencies in an isolated virtual environment. Resolved yt-dlp 2026.8.19, pynput 1.8.2, pyperclip 1.11.0, and yt-dlp-ejs 0.8.0.
- Portable unit tests cover URL normalization/rejection, configuration errors, format arguments, OS lock exclusion/release, success-file verification, downloader failure/cancellation, clipboard failure, shortcut dispatch for both formats, permission rejection, Wayland routing, and doctor failure.
- Opt-in integration test generates one second of synthetic H.264/AAC content, serves it on loopback, runs the actual yt-dlp subprocess for MP4 and MP3, and decodes both outputs with FFmpeg. The MP4 contains video and audio; the MP3 contains MP3 audio. Test-only FFmpeg came from imageio-ffmpeg 0.6.0.
- The integration test substitutes the YouTube URL validator and dependency preflight because its source is local synthetic media. It does **not** prove YouTube extraction, Deno execution, ffprobe availability, or clipboard/keyboard behavior.
- Built wheel and source distribution with setuptools; the source distribution includes docs, tests, and skill files.
- CLI help/version, Python dependency consistency, whitespace checks, and the bundled skill-creator validator pass.

## Reproduce

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

Portable run: 12 tests pass, one media test skips by design. For the real media test, install FFmpeg on PATH (or install the optional test helper `imageio-ffmpeg`), then:

```sh
VYBE_MEDIA_TESTS=1 python -m unittest discover -s tests -v
```

PowerShell: set `$env:VYBE_MEDIA_TESTS='1'` before the same Python command. This run contains 13 tests. The local fixture uses no third-party video content.

To validate skill metadata and build distributions, install `PyYAML`, `build`, `setuptools`, and `wheel` in the development environment. Use your skill-creator installation's `scripts/quick_validate.py skills/vybe`, then `python -m build`.

## Still requires desktop/site verification

- Actual YouTube downloads with FFmpeg, ffprobe, and Deno installed in the target launch environment.
- Physical shortcut presses, real clipboard reads, macOS permission prompts, and background/login startup.
- Windows and Linux desktop behavior, including X11 and each Wayland clipboard backend.

For each target desktop: run `doctor`, start `run` (or native Wayland shortcuts), copy a permitted YouTube video URL, trigger MP4 and MP3 separately, inspect logs, then run `ffprobe -v error -show_format -show_streams FILE` on each output. Check duplicate presses, invalid clipboard text, cancellation, and restart after login. Record results before claiming that desktop is verified.

GitHub Actions is configured for six portable OS/Python combinations and a Linux FFmpeg integration job. Configuration alone is not a passing CI result; consult the actual run for the relevant commit.

## Public CI follow-up

The [first public run](https://github.com/mickfive05/VYBE/actions/runs/39665816265)
passed the macOS and Ubuntu portable jobs and the Linux media integration job.
Windows exposed two problems: the listener tests patched the shared
`sys.platform` value and selected an unavailable POSIX lock backend; a competing
Windows byte-range lock could also reject the initial lock-file read before
the intended contention handler ran.

The beta changes isolate the simulated platform to the CLI module and include
that initial read in the contention handler. The existing nested-lock test
exercises exclusion and release on the actual CI operating system. The
[workflow badge](https://github.com/mickfive05/VYBE/actions/workflows/tests.yml)
links to the latest result; desktop permissions, physical shortcut presses,
and actual YouTube extraction remain separate manual checks.
