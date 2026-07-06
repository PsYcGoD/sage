"""Create lightweight starter GIFs for SAGE docs."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ASSET_DIR = Path("docs/assets")
SIZE = (900, 420)


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("CascadiaMono.ttf", "consola.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _frame(title: str, lines: list[str], accent: str = "#22c55e") -> Image.Image:
    image = Image.new("RGB", SIZE, "#0f172a")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIZE[0], 46), fill="#111827")
    for index, color in enumerate(("#ef4444", "#f59e0b", "#22c55e")):
        draw.ellipse((22 + index * 22, 17, 34 + index * 22, 29), fill=color)
    draw.text((24, 72), title, fill=accent, font=_font(26))
    y = 122
    for line in lines:
        draw.text((24, y), line, fill="#e5e7eb", font=_font(20))
        y += 36
    return image


def _save(name: str, frames: list[Image.Image]) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        ASSET_DIR / name,
        save_all=True,
        append_images=frames[1:],
        duration=900,
        loop=0,
    )


def main() -> int:
    _save(
        "demo-sage-run.gif",
        [
            _frame("$ sage run -- python -m pytest", ["Running tests through SAGE...", "Raw output stays local."]),
            _frame("[sage] compressed output", ["Saved 12,480 tokens", "Summary sent to the agent.", "Raw logs preserved locally."]),
        ],
    )
    _save(
        "demo-sage-savings.gif",
        [
            _frame("$ sage savings --agent claude-sonnet", ["Calculating savings from local proof rows..."]),
            _frame("SAGE savings estimate", ["Saved tokens: 15,177,748", "Compression rate: 92.9%", "Estimated savings: proof only."]),
        ],
    )
    _save(
        "demo-github-bot.gif",
        [
            _frame("$ sage github-bot comment --kind summary", ["Generating PR-ready Markdown..."]),
            _frame("SAGE Bot comment", ["Status, policy, redactions", "Token savings proof", "No raw logs uploaded."]),
        ],
    )
    print("Demo GIFs written to docs/assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
