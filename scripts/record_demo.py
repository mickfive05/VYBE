"""Render a truthful GIF replay of the real synthetic-media test.

Development only: requires Pillow; the test interpreter needs VYBE and FFmpeg
or imageio-ffmpeg. No desktop clipboard or keyboard events are simulated.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont


def font(size, mono=False):
    candidates = (["/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
                  if mono else ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for name in candidates:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, VYBE_MEDIA_TESTS="1")
    run = subprocess.run([args.python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_media.py", "-v"],
                         cwd=root, env=env, capture_output=True, text=True)
    if run.returncode:
        print(run.stdout + run.stderr, file=sys.stderr)
        raise SystemExit(run.returncode)
    milestones = [line.split("VYBE DEMO | ", 1)[1] for line in run.stdout.splitlines() if "VYBE DEMO | " in line]
    if len(milestones) != 3:
        raise SystemExit("Expected all three successful media-test milestones")
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    transcript = "Command: VYBE_MEDIA_TESTS=1 python -m unittest discover -s tests -p test_media.py -v\n\n" + "\n".join(milestones) + "\n\nResult: media test passed. Local synthetic content; desktop shortcuts and YouTube are not exercised.\n"
    (assets / "demo-transcript.txt").write_text(transcript, encoding="utf-8")

    def frame(count):
        image = Image.new("RGB", (1100, 530), "#101617")
        draw = ImageDraw.Draw(image)
        draw.text((42, 30), "VYBE", font=font(44), fill="#d8f581")
        draw.text((42, 91), "One link. Video or audio.", font=font(25), fill="#f2f1e9")
        draw.rounded_rectangle((40, 155, 1060, 424), radius=16, fill="#1c2525", outline="#354140", width=2)
        draw.text((66, 178), "LOCAL MEDIA TEST / ACTUAL OUTPUT REPLAY", font=font(18, True), fill="#9daead")
        draw.text((66, 226), "$ python -m unittest discover -s tests -p test_media.py", font=font(18, True), fill="#d9dfda")
        for index, line in enumerate(milestones[:count]):
            # Wrap the filename onto a second line in the source transcript only;
            # the compact display preserves the verified milestone text.
            label = line.split(": fixture", 1)[0]
            draw.text((66, 278 + index * 39), label, font=font(18, True), fill="#d8f581")
        draw.text((42, 455), "Synthetic content. No YouTube request or physical shortcut test.", font=font(20), fill="#a6b5b3")
        draw.text((42, 491), "Reproduce: docs/DEMO.md", font=font(17), fill="#a6b5b3")
        return image

    frames = [frame(index) for index in range(4)]
    frames[0].save(assets / "demo.gif", save_all=True, append_images=frames[1:], duration=[900, 1400, 1400, 3000], loop=0)
    social = Image.new("RGB", (1280, 640), "#101617")
    draw = ImageDraw.Draw(social)
    draw.rectangle((64, 72, 72, 568), fill="#d8f581")
    draw.text((108, 78), "VYBE", font=font(92), fill="#d8f581")
    draw.text((112, 214), "Copy the link.", font=font(48), fill="#f2f1e9")
    draw.text((112, 278), "Press the shortcut.", font=font(48), fill="#f2f1e9")
    draw.text((112, 342), "Keep the moment.", font=font(48), fill="#f2f1e9")
    draw.text((112, 462), "CTRL + ALT + V    MP4", font=font(25, True), fill="#d8f581")
    draw.text((112, 510), "CTRL + ALT + A    MP3", font=font(25, True), fill="#d8f581")
    draw.text((112, 590), "Local utility / yt-dlp + FFmpeg / Early preview", font=font(21), fill="#a6b5b3")
    social.save(assets / "social-preview.png")
    print("Media test passed; demo GIF, transcript, and social preview generated.")


if __name__ == "__main__":
    main()
