# Help improve VYBE

VYBE is an early project. Reproducible bug reports and real desktop testing
are the most useful contributions right now.

## Licensing first

VYBE currently reserves all rights; it is not released under an open-source
license. See [LICENSE](LICENSE). Please open an issue before submitting code
so the maintainer can agree scope and contribution terms with you. This guide
does not grant a license or imply a transfer of rights.

## Report a bug

Use the Bug report issue form. Include your OS/version, Python and VYBE
versions, desktop session (X11/Wayland on Linux), exact command or shortcut,
expected behavior, and sanitized diagnostics. Try the one-shot download
command to distinguish extraction failures from keyboard integration issues.
Do not post clipboard contents, private video links, cookies, tokens,
personal paths, or unredacted logs.

## Help verify a desktop

Use the Desktop verification form. Follow [the verification procedure](docs/VERIFICATION.md)
and report each check independently: dependencies, clipboard, MP4, MP3,
physical shortcuts, cancellation, and optional background startup. Mark any
check you did not run as untested. Use only content you are permitted to save.

Small first tasks include checking the Windows installation instructions or
documenting exact native shortcut steps for one Wayland desktop. Findings
can be submitted as an issue; code changes are not required.

## Development, when authorized

Use a separate virtual environment and install the checkout with
`python -m pip install -e .`. Run `python -m unittest discover -s tests -v`.
For the optional media check, install FFmpeg and set `VYBE_MEDIA_TESTS=1`.
That test serves synthetic media on loopback and does not verify YouTube.
Keep changes focused, describe observable behavior, and include relevant
test results. Never add a passing badge or claim a platform works without evidence.
