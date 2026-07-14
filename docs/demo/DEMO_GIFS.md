# Demo GIFs and 30-second video

Goal: create short GIFs that show SAGE value before asking users to install.

## Generated real assets

These were generated from actual local SAGE command output using:

```bash
python scripts/create_demo_video_assets.py
```

Outputs:

- `docs/assets/sage-demo-01-first-impression.gif`
- `docs/assets/sage-demo-02-real-compression.gif`
- `docs/assets/sage-demo-03-proof-loop.gif`
- `docs/assets/sage-30s-real-demo.mp4`

The GIFs are split into three ~10-second sections:

1. First impression: `sage demo`
2. Real compression: `sage run -- rg ...` on this repo
3. Proof loop: `sage history --limit 3`

The MP4 combines the same three parts into one ~30-second video.

## GIF 1: `sage run --`

Show a noisy command being wrapped by SAGE:

```bash
sage run -- python -m pytest
```

End frame:

```text
[sage] context: saved tokens
Raw logs remain local.
```

## GIF 2: Savings Proof

Show:

```bash
sage savings --agent claude-sonnet
```

End frame:

```text
Saved tokens
Compression rate
Estimated savings
```

## GIF 3: Dashboard Proof

Show the dashboard with:

```bash
sage dashboard start --port 8765
```

Focus on total commands, tokens saved, compression rate, and success rate.

## GIF 4: GitHub Bot Comment

Show:

```bash
sage github-bot comment --kind summary
```

End frame shows a PR-ready Markdown comment that contains only aggregate proof and redacted local summary data.

## Recording Notes

- Keep each GIF under 20 seconds.
- Do not show real secrets, private paths, or raw logs.
- Use a demo repo with synthetic output.
- Put final GIFs in `docs/assets/`.
