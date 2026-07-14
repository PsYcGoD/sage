from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
OUT_GIFS = [
    ASSETS / "sage-demo-01-first-impression.gif",
    ASSETS / "sage-demo-02-real-compression.gif",
    ASSETS / "sage-demo-03-proof-loop.gif",
]
OUT_MP4 = ASSETS / "sage-30s-real-demo.mp4"


def run_real_command(args: list[str]) -> str:
    env = os.environ.copy()
    env["SAGE_SKIP_SETUP"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    proc = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    command = " ".join(args)
    return f"$ {command}\n\n{proc.stdout.strip()}\n\n(exit {proc.returncode})"


def capture_segments() -> list[tuple[str, str]]:
    python = sys.executable
    real_search_pattern = r"def |class |ERROR|TODO|return "
    segment_1 = run_real_command([python, "-m", "sage", "demo"])
    segment_2 = run_real_command(
        [
            python,
            "-m",
            "sage",
            "run",
            "--",
            "rg",
            "-n",
            real_search_pattern,
            "src",
            "tests",
        ]
    )
    segment_3 = run_real_command([python, "-m", "sage", "history", "--limit", "3"])
    return [
        ("1/3: First 15-second value", segment_1),
        ("2/3: Real repo command compressed by SAGE", segment_2),
        ("3/3: Proof saved locally for agents", segment_3),
    ]


def load_font(size: int):
    from PIL import ImageFont

    for candidate in [
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/CascadiaMono.ttf"),
        Path("C:/Windows/Fonts/lucon.ttf"),
    ]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def wrap_line(draw, text: str, font, max_width: int) -> list[str]:
    if not text:
        return [""]
    chunks: list[str] = []
    current = ""
    for token in re.split(r"(\s+)", text):
        trial = current + token
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
            continue
        if current.strip():
            chunks.append(current.rstrip())
        current = token.lstrip()
    if current.strip() or not chunks:
        chunks.append(current.rstrip())
    return chunks


def prepare_lines(draw, title: str, content: str, font, max_width: int, max_lines: int) -> list[str]:
    lines = [title, "=" * min(70, len(title) + 18), ""]
    important = []
    for raw in content.splitlines():
        line = raw.rstrip()
        if not line:
            important.append("")
            continue
        lower = line.lower()
        if (
            line.startswith("$ ")
            or line.startswith("[sage]")
            or "saved" in lower
            or "compressed" in lower
            or "before:" in lower
            or "after:" in lower
            or "try it" in lower
            or "real repo command" in lower
            or "exit " in lower
            or len(important) < 20
        ):
            important.append(line)
    for raw in important:
        lines.extend(wrap_line(draw, raw, font, max_width))
        if len(lines) >= max_lines:
            lines.append("...")
            break
    return lines[:max_lines]


def make_frames(title: str, content: str, frame_count: int = 20):
    from PIL import Image, ImageDraw

    width, height = 1280, 720
    pad = 44
    font = load_font(24)
    small = load_font(20)
    tmp = Image.new("RGB", (width, height))
    d = ImageDraw.Draw(tmp)
    lines = prepare_lines(d, title, content, font, width - pad * 2, 22)

    frames = []
    for idx in range(frame_count):
        reveal = max(1, round(len(lines) * ((idx + 1) / frame_count)))
        img = Image.new("RGB", (width, height), "#0b1020")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, width, 66), fill="#111827")
        draw.text((pad, 20), "SAGE real terminal demo", fill="#55f991", font=small)
        draw.text((width - 300, 20), "local-first token compression", fill="#93c5fd", font=small)
        y = 96
        for n, line in enumerate(lines[:reveal]):
            color = "#e5e7eb"
            if n == 0:
                color = "#55f991"
            elif line.startswith("$ "):
                color = "#fbbf24"
            elif line.startswith("[sage]"):
                color = "#93c5fd"
            elif "Saved:" in line or "saved" in line.lower():
                color = "#86efac"
            elif "exit 1" in line:
                color = "#fca5a5"
            draw.text((pad, y), line, fill=color, font=font)
            y += 29
            if y > height - 72:
                break
        draw.rectangle((pad, height - 46, width - pad, height - 42), fill="#374151")
        draw.rectangle((pad, height - 46, pad + int((width - pad * 2) * ((idx + 1) / frame_count)), height - 42), fill="#55f991")
        frames.append(img)
    return frames


def save_gif(path: Path, frames) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=500,
        loop=0,
        optimize=True,
    )


def save_mp4(gif_frames: list[list], out: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    with tempfile.TemporaryDirectory(prefix="sage-demo-frames-") as tmpdir:
        tmp = Path(tmpdir)
        idx = 0
        for frames in gif_frames:
            for frame in frames:
                frame.save(tmp / f"frame_{idx:04d}.png")
                idx += 1
        cmd = [
            ffmpeg,
            "-y",
            "-framerate",
            "2",
            "-i",
            str(tmp / "frame_%04d.png"),
            "-vf",
            "format=yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return True


def main() -> int:
    try:
        import PIL  # noqa: F401
    except Exception as exc:
        print(f"Pillow is required to render GIFs: {exc}", file=sys.stderr)
        return 1

    segments = capture_segments()
    all_frames = []
    for (title, content), gif_path in zip(segments, OUT_GIFS, strict=True):
        frames = make_frames(title, content)
        save_gif(gif_path, frames)
        all_frames.append(frames)
        print(f"wrote {gif_path}")

    if save_mp4(all_frames, OUT_MP4):
        print(f"wrote {OUT_MP4}")
    else:
        print("ffmpeg not found; skipped mp4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
