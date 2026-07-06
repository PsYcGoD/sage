# SAGE Cloudflare API

Public SAGE API Worker for opt-in telemetry, API key bootstrap, and aggregate proof counters.

## Deployed Resources

| Resource | Name |
|---|---|
| Worker | `sage-api` |
| Current public Worker | `https://psyc-god-sage-api.valan-dj.workers.dev` |
| Previous custom domain | `https://sage.api.marketingstudios.in` |
| D1 database | `sage_telemetry` |
| D1 database ID | `30dce3a3-6f7f-423c-9f29-4ff812685752` |
| Queue | `sage-telemetry-queue` |
| R2 bucket | `sage-redacted-artifacts` |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Worker health check |
| `POST` | `/v1/keys` | Create a free SAGE API key. The full key is returned once. |
| `POST` | `/v1/telemetry` | Upload safe opt-in telemetry using `Authorization: Bearer <key>`. |
| `GET` | `/v1/proof` | Public aggregate proof counters. |

## Public Proof Fields

The proof endpoint exposes:

- Total runs.
- Successful runs.
- Failed runs.
- Tokens processed.
- Tokens compressed.
- Tokens saved.
- Compression percent.
- Success rate.
- Failure-prediction event count and average score.
- Public contributors: display/profile name and username only when a user opts into public profile display. Multiple API keys for the same public profile are aggregated together.

The proof endpoint does not expose raw commands, raw output, file paths, repository names, file contents, or secrets.

## Deploy

```powershell
Set-Location D:\work\sage\cloudflare\sage-api
npx wrangler d1 execute sage_telemetry --remote --file schema/schema.sql
npx wrangler deploy
```

## Verify

```powershell
Set-Location D:\work\sage
powershell -NoProfile -ExecutionPolicy Bypass -File .\cloudflare\sage-api\scripts\verify_api.ps1
```

The verification script creates a redacted founder/test key, sends one Level 1 telemetry event, and prints public proof totals without printing the full API key.

## User Start Flow

Start SAGE locally:

```powershell
cd D:\work\sage
sage gui
```

Connect from the GUI:

```text
Settings -> SAGE Cloud API -> Connect SAGE API
```

The GUI creates the free API key, stores it locally, and connects SAGE to the public API. Users do not need to copy or paste API keys.

Sync from the GUI:

```text
Settings -> SAGE Cloud API -> Sync Now
```

After a user connects, normal `sage run -- <command>` calls also queue and sync safe proof metrics automatically in the background. `Sync Now` is only a manual retry button.

CLI fallback:

```powershell
sage login --display-name "Your Name" --username "your-handle" --public-profile --privacy-max 1
sage whoami
sage api status
```

Run commands locally as usual:

```powershell
sage run -- python -m pytest
sage telemetry queue
sage telemetry send --for-real
```

Public proof:

```text
https://psyc-god-sage-api.valan-dj.workers.dev/v1/proof
```

The fallback endpoint remains:

```text
https://sage.api.marketingstudios.in/v1/proof
```
