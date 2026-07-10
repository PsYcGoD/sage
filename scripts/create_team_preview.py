"""Create the Team Dashboard preview image used in README."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "CascadiaMono.ttf", "consola.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    width, height = 1200, 760
    image = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, 72), fill="#111827")
    draw.text((36, 24), "SAGE Team View Preview", fill="#f8fafc", font=_font(30))
    draw.text((880, 28), "Enterprise-only access", fill="#a7f3d0", font=_font(18))

    cards = [
        ("Workspaces", "12"),
        ("Tokens saved", "15.1M"),
        ("Safety events", "38"),
        ("Success rate", "96.7%"),
    ]
    x = 36
    for title, value in cards:
        draw.rounded_rectangle((x, 110, x + 255, 245), radius=14, fill="#1e293b", outline="#334155")
        draw.text((x + 22, 132), title, fill="#94a3b8", font=_font(18))
        draw.text((x + 22, 170), value, fill="#a7f3d0", font=_font(38))
        x += 282

    draw.rounded_rectangle((36, 285, 1164, 690), radius=14, fill="#111827", outline="#334155")
    draw.text((64, 315), "Workspace proof snapshot", fill="#f8fafc", font=_font(24))

    rows = [
        ("api-service", "1,204 runs", "94.1% saved", "2 secrets protected"),
        ("web-dashboard", "884 runs", "91.8% saved", "0 blocked commands"),
        ("agent-sandbox", "2,046 runs", "93.7% saved", "12 risky commands blocked"),
    ]
    y = 370
    for name, runs, saved, safety in rows:
        draw.rounded_rectangle((64, y, 1136, y + 78), radius=8, fill="#1e293b")
        draw.text((90, y + 22), name, fill="#e5e7eb", font=_font(20))
        draw.text((360, y + 22), runs, fill="#bfdbfe", font=_font(18))
        draw.text((570, y + 22), saved, fill="#a7f3d0", font=_font(18))
        draw.text((800, y + 22), safety, fill="#fef3c7", font=_font(18))
        y += 96

    draw.text(
        (64, 716),
        "Preview only: Team View is available for Enterprise customers.",
        fill="#cbd5e1",
        font=_font(18),
    )

    out = Path("docs/assets/team-dashboard-preview.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    print(f"Team Dashboard preview written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
