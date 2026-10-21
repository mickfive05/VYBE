---
name: vybe
description: Install, configure, diagnose, or use VYBE, a local YouTube clipboard downloader with MP4 and MP3 desktop shortcuts. Use for VYBE requests, not general video editing or unrelated download tools.
---

# VYBE

VYBE runs on the target desktop. A remote ChatGPT runtime cannot register its shortcuts or read its clipboard.

Locate the user's VYBE checkout and environment. If absent, obtain it from `https://github.com/mickfive05/VYBE` in the requested workspace. Read the checkout's `docs/INSTALL.md` for platform setup and `docs/VERIFICATION.md` for actual verification limits. This skill does not bundle the application.

Use Python 3.10+, install the checkout into a virtual environment, and check FFmpeg, ffprobe, Deno, and yt-dlp's default extras. Run `vybe doctor`. Dependency access, clipboard access, keyboard permission, and successful media conversion are separate checks.

- `vybe run` listens for Ctrl+Alt+V (MP4) and Ctrl+Alt+A (MP3), unless configured otherwise.
- `vybe download mp4` or `vybe download mp3` reads one URL from the local clipboard.
- For a supplied URL, use `vybe download mp4 --url URL` (or mp3) with separate process arguments. Never interpolate clipboard text into a shell command.
- `vybe --config /absolute/config.json run` selects JSON settings: `output`, `mp4_hotkey`, and `mp3_hotkey`. Preserve user choices.

On macOS, explain Accessibility/Input Monitoring permissions and test real shortcut behavior after restart. On Linux X11, use the logged-in desktop session. On Wayland, configure two native shortcuts invoking the one-shot download commands. Check clipboard backend availability separately; do not promise universal Wayland support.

Keep startup observable until checks pass. Starting a process does not prove it stayed alive or registered shortcuts. Inspect logs, test both formats on content the user may download, verify final files, and use ffprobe to inspect media tracks when testing downloads. Report what ran and what remains untested.

One download at a time is intentional. Do not start duplicate listeners, silently install login tasks, bypass access restrictions, or claim a remote session changed a local desktop. If local execution is unavailable, provide platform commands and identify the unverified steps.
