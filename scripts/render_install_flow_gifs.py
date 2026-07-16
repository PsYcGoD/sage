from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"

W, H = 920, 560
BG = (11, 18, 32)
PANEL = (17, 27, 46)
HEADER = (31, 45, 68)
TEXT = (229, 236, 246)
MUTED = (148, 163, 184)
GREEN = (52, 211, 153)
YELLOW = (250, 204, 21)
BLUE = (96, 165, 250)
RED = (248, 113, 113)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/CascadiaMono.ttf",
        "C:/Windows/Fonts/CascadiaCode.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


MONO = font(22)
MONO_SMALL = font(18)
TITLE = font(24, bold=True)


def terminal_frame(title: str, lines: list[tuple[str, tuple[int, int, int]]], cursor: bool = False) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((36, 34, W - 36, H - 34), radius=14, fill=PANEL, outline=(51, 65, 85), width=2)
    draw.rounded_rectangle((36, 34, W - 36, 84), radius=14, fill=HEADER)
    draw.rectangle((36, 70, W - 36, 84), fill=HEADER)
    draw.ellipse((58, 52, 72, 66), fill=RED)
    draw.ellipse((82, 52, 96, 66), fill=YELLOW)
    draw.ellipse((106, 52, 120, 66), fill=GREEN)
    draw.text((142, 50), title, fill=TEXT, font=TITLE)

    y = 112
    for line, color in lines:
        draw.text((62, y), line, fill=color, font=MONO)
        y += 34

    if cursor:
        x = 62 + max((len(lines[-1][0]) if lines else 0), 1) * 13
        draw.rectangle((x, y - 32, x + 12, y - 8), fill=GREEN)
    return img


def typing_frames(title: str, before: list[tuple[str, tuple[int, int, int]]], command: str) -> list[Image.Image]:
    frames: list[Image.Image] = []
    for i in range(0, len(command) + 1, 4):
        typed = command[:i]
        frames.append(terminal_frame(title, before + [(f"$ {typed}", GREEN)], cursor=True))
    frames.append(terminal_frame(title, before + [(f"$ {command}", GREEN)]))
    return frames


def render_gif(filename: str, title: str, command: str, output: list[tuple[str, tuple[int, int, int]]]) -> None:
    frames = typing_frames(title, [], command)
    current: list[tuple[str, tuple[int, int, int]]] = [(f"$ {command}", GREEN)]
    for line in output:
        current.append(line)
        frames.append(terminal_frame(title, current))
    frames.extend([frames[-1]] * 10)
    frames[0].save(
        OUT / filename,
        save_all=True,
        append_images=frames[1:],
        duration=[65] * (len(frames) - 10) + [180] * 10,
        loop=0,
        optimize=True,
    )


def render_diagram() -> None:
    img = Image.new("RGB", (1500, 700), (248, 250, 252))
    draw = ImageDraw.Draw(img)
    title = font(34, bold=True)
    body = font(22)
    small = font(18)
    draw.text((52, 36), "SAGE explicit install flow", fill=(15, 23, 42), font=title)
    draw.text((54, 86), "npm and PyPI installs stay passive. The user explicitly runs install once.", fill=(71, 85, 105), font=body)

    boxes = [
        ("1. Package install", "npm install -g psycgod-sage\nor pip install psycgod-sage", (56, 180)),
        ("2. Explicit setup", "npx -y psycgod-sage install\nor sage install", (426, 180)),
        ("3. Activation logic", "machine id + API connect\nagent memory + hooks", (796, 180)),
        ("4. Agent ready", "restart agent session\ncommands use sage run --", (1166, 180)),
    ]
    for i, (heading, text, (x, y)) in enumerate(boxes):
        draw.rounded_rectangle((x, y, x + 285, y + 220), radius=12, fill=(255, 255, 255), outline=(203, 213, 225), width=2)
        draw.text((x + 20, y + 22), heading, fill=(15, 23, 42), font=body)
        yy = y + 76
        for line in text.splitlines():
            draw.text((x + 20, yy), line, fill=(51, 65, 85), font=small)
            yy += 32
        if i < len(boxes) - 1:
            ax = x + 300
            ay = y + 110
            draw.line((ax, ay, ax + 52, ay), fill=(37, 99, 235), width=5)
            draw.polygon([(ax + 52, ay), (ax + 36, ay - 10), (ax + 36, ay + 10)], fill=(37, 99, 235))

    draw.rounded_rectangle((56, 480, 1444, 610), radius=12, fill=(239, 246, 255), outline=(147, 197, 253), width=2)
    draw.text((84, 504), "Result", fill=(30, 64, 175), font=body)
    draw.text(
        (84, 542),
        "No hidden npm postinstall activation. The user chooses install, then SAGE safely injects instructions and hooks.",
        fill=(30, 64, 175),
        font=small,
    )
    img.save(OUT / "sage-install-flow-diagram.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    render_gif(
        "sage-install-npm.gif",
        "npm / npx onboarding",
        "npx -y psycgod-sage install",
        [
            ("Installing Python SAGE core from PyPI...", MUTED),
            ("SAGE install", BLUE),
            ("Configuring automatically with this machine identity.", TEXT),
            ("Identity: DESKTOP-7AEF5452", TEXT),
            ("Cloud connection: connected", GREEN),
            ("Global AI-agent memory/hooks: verified", GREEN),
            ("Project AI-agent memory/hooks: updated", GREEN),
            ("SAGE installed successfully.", GREEN),
            ("Press Enter to finish.", YELLOW),
        ],
    )
    render_gif(
        "sage-install-pypi.gif",
        "PyPI / pip onboarding",
        "sage install",
        [
            ("SAGE install", BLUE),
            ("Configuring automatically with this machine identity.", TEXT),
            ("Identity: workstation-7aef5452", TEXT),
            ("Cloud connection: connected", GREEN),
            ("Global AI-agent memory/hooks: verified", GREEN),
            ("Project AI-agent memory/hooks: updated", GREEN),
            ("Verification: activation doctor passed", GREEN),
            ("SAGE installed successfully.", GREEN),
            ("Press Enter to finish.", YELLOW),
        ],
    )
    render_diagram()
    print("Generated:")
    print(OUT / "sage-install-npm.gif")
    print(OUT / "sage-install-pypi.gif")
    print(OUT / "sage-install-flow-diagram.png")


if __name__ == "__main__":
    main()
