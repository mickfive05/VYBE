# Installation and operation

## Requirements

Use Python 3.10+, Git, FFmpeg **with ffprobe**, and Deno on PATH. The Python package named ffmpeg is not a substitute for the executables. VYBE installs yt-dlp's default extras, including its YouTube JavaScript support components.

References: [yt-dlp dependencies](https://github.com/yt-dlp/yt-dlp#dependencies), [YouTube JavaScript support](https://github.com/yt-dlp/yt-dlp/wiki/EJS), [pynput platform limits](https://pynput.readthedocs.io/en/latest/limitations.html), [pyperclip backends](https://github.com/asweigart/pyperclip), [FFmpeg downloads](https://ffmpeg.org/download.html), [Deno installation](https://docs.deno.com/runtime/getting_started/installation/).

## Windows (PowerShell)

Install [Python](https://www.python.org/downloads/windows/) and [Git](https://git-scm.com/downloads/win). With Windows Package Manager:

```powershell
winget install --id Gyan.FFmpeg --exact
winget install --id DenoLand.Deno --exact
```

Open a new terminal for PATH changes, then:

```powershell
git clone https://github.com/mickfive05/VYBE.git
cd VYBE
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\vybe.exe doctor
.\.venv\Scripts\vybe.exe run
```

Choose a Python 3.10+ interpreter if `py -3` selects an older version. No environment activation or execution-policy change is needed. Run in your logged-in desktop session and avoid shortcut conflicts.

## macOS

With [Homebrew](https://brew.sh/):

```sh
brew install python ffmpeg deno git
git clone https://github.com/mickfive05/VYBE.git
cd VYBE
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/vybe doctor
.venv/bin/vybe run
```

In System Settings → Privacy & Security, grant **Accessibility** and, when requested, **Input Monitoring** to the terminal/Python used by the listener. Quit and restart after changing permissions. Background launch can have a different permission identity, so test that method separately. VYBE checks the listener trust flag; a physical shortcut test is still necessary. Do not run as root to work around permissions.

## Linux

On Debian/Ubuntu:

```sh
sudo apt update
sudo apt install python3 python3-venv ffmpeg git xclip
```

Install Deno using its [official instructions](https://docs.deno.com/runtime/getting_started/installation/) or a supported distribution package. Follow the macOS clone and environment commands above, starting at `git clone`. Other distributions use their own package managers.

**X11:** launch in your desktop session with its existing DISPLAY and a pyperclip clipboard backend such as xclip/xsel. Do not invent a display value. SSH/headless sessions are not equivalent to a desktop session.

**Wayland:** VYBE refuses listener mode when `XDG_SESSION_TYPE=wayland`, since pynput cannot reliably receive global events across applications. Configure two custom shortcuts in GNOME/KDE/your compositor:

```text
/absolute/path/to/VYBE/.venv/bin/vybe download mp4
/absolute/path/to/VYBE/.venv/bin/vybe download mp3
```

Clipboard support depends separately on the installed pyperclip backend. Run `doctor` in the same session. If clipboard access is unavailable, install a compatible backend or use an OS-specific wrapper passing the URL with `--url`. Universal Wayland clipboard support is not guaranteed.

## Configuration and logs

| System | Data directory |
| --- | --- |
| Windows | `%LOCALAPPDATA%\VYBE` |
| macOS | `~/Library/Application Support/VYBE` |
| Linux | `$XDG_STATE_HOME/vybe`, default `~/.local/state/vybe` |

Create `config.json` there using the README example. Fields `output`, `mp4_hotkey`, and `mp3_hotkey` must be nonempty strings. Unknown fields and invalid JSON fail clearly. Missing config uses defaults. `~` expands; relative output paths resolve from the working directory, so prefer absolute paths for background use.

Use `vybe --config /absolute/config.json run` for another file. `--config` precedes the subcommand; `--output` belongs to `download` only. Shortcut syntax follows [pynput HotKey](https://pynput.readthedocs.io/en/latest/keyboard.html#global-hotkeys). Restart after editing settings.

`vybe.log` contains application messages and rotates at 1 MB with three backups. yt-dlp diagnostics go to process output; capture them for background use. Diagnostics can contain titles, paths, and URLs; review before sharing. Clipboard contents are read on activation or a one-shot download; doctor checks clipboard access without displaying its contents.

## Background operation and login startup

First check `doctor`, foreground `run`, and both physical shortcuts. VYBE has no GUI, tray icon, built-in service installer, or stop command. Repeated presses while a download is active are ignored; competing downloads fail with an already-running message. Ctrl+C/SIGTERM cancels the downloader; partial files may remain for resumption. Live streams may keep downloading until stopped.

**macOS/Linux:** after foreground verification:

```sh
nohup /absolute/path/to/VYBE/.venv/bin/vybe run >> "$HOME/vybe-output.log" 2>&1 &
echo $!
```

Record the PID. Stop it with `kill PID` or your process manager. For login startup, add the absolute command to desktop login applications or a user LaunchAgent on macOS. Configure PATH to include FFmpeg/Deno: shell startup files may not be loaded. Verify logs, permissions, and shortcuts after launch. Avoid system/headless services without the desktop session.

**Windows:** after `doctor` creates the data directory, launch without a console:

```powershell
Start-Process -FilePath 'C:\absolute\VYBE\.venv\Scripts\pythonw.exe' -ArgumentList '-m','vybe','run' -RedirectStandardOutput "$env:LOCALAPPDATA\VYBE\stdout.log" -RedirectStandardError "$env:LOCALAPPDATA\VYBE\stderr.log" -PassThru
```

Record its PID and test both shortcuts. Stop that PID using Task Manager or `Stop-Process -Id PID`. Forced termination may leave partial files. For login startup, configure Task Scheduler for your user, **Run only when user is logged on**, with the same executable, arguments, and PATH. No elevation is needed. Configure output capture when diagnosing startup failures.

The redirected output files in these examples do not rotate; rotate or delete them periodically while stopped. VYBE does not install any login task automatically.

## Troubleshooting

- Missing dependencies: check `ffmpeg -version`, `ffprobe -version`, `deno --version` in the launch environment; reopen the terminal after installation.
- Clipboard failure: copy text, install a compatible backend, and test from the same desktop session.
- No shortcut response: check conflicts, permissions, platform/session type, and process health. Try `vybe download mp4` to isolate keyboard integration.
- yt-dlp failure: inspect its captured diagnostics and update dependencies. A video may be unavailable, restricted, or blocked. VYBE does not automatically import browser cookies or bypass access controls.
- MP4 unavailable: compatible MP4/M4A source formats are required. VYBE does not silently substitute WebM.
- Existing file: no overwrite is performed. Move/remove it deliberately to download afresh.

## Update and uninstall

Stop the listener, update the checkout, and use its environment's Python:

```sh
git pull --ff-only
python -m pip install --upgrade .
```

Restart and verify. To uninstall: stop VYBE, remove any login task you added, run `python -m pip uninstall vybe-clipboard`, and optionally delete its environment and data directory. Downloaded files remain in your output folder.
