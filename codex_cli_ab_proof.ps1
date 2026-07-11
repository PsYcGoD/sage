param(
  [string]$Model = "",
  [string]$PricePerMillionInput = "1.50",
  [string]$OutDir = "codex-ab-proof"
)

$ErrorActionPreference = "Stop"

$ScriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
$ProofDir = if ([System.IO.Path]::IsPathRooted($OutDir)) { $OutDir } else { Join-Path $ScriptRoot $OutDir }
New-Item -ItemType Directory -Force -Path $ProofDir | Out-Null

$rawPrompt = Join-Path $ProofDir "without-sage-raw-prompt.txt"
$sagePrompt = Join-Path $ProofDir "with-sage-compressed-prompt.txt"
$rawJsonl = Join-Path $ProofDir "without-sage-codex.jsonl"
$sageJsonl = Join-Path $ProofDir "with-sage-codex.jsonl"
$reportPath = Join-Path $ProofDir "codex-ab-report.json"

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("Reply with exactly OK. Do not run tools. Terminal output follows:")
$lines.Add("pytest tests/test_payments.py::test_checkout_flow FAILED")
for ($i = 0; $i -lt 1800; $i++) {
  $lineNumber = 120 + ($i % 30)
  $lines.Add(("E AssertionError: expected status 200 got 500 | request_id=req_{0:D4} | stack frame app/payments.py:{1}" -f $i, $lineNumber))
}
[IO.File]::WriteAllLines($rawPrompt, $lines)

$compressed = @"
Reply with exactly OK. Do not run tools. Terminal output follows:
Tests: passed=0 failed=1 skipped=0
Summary: E AssertionError: expected status 200 got 500 | request_id=req_1799 | stack frame app/payments.py:149
Failed:
  - pytest tests/test_payments.py::test_checkout_flow FAILED
"@
[IO.File]::WriteAllText($sagePrompt, $compressed)

function Invoke-CodexProofRun {
  param(
    [string]$PromptPath,
    [string]$OutputPath
  )

  $args = @("exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only")
  if ($Model.Trim()) {
    $args += @("--model", $Model)
  }
  $args += @("-")

  Get-Content -Raw -LiteralPath $PromptPath | & codex @args | Tee-Object -FilePath $OutputPath
}

function Read-Jsonl {
  param([string]$Path)
  $events = @()
  if (-not (Test-Path -LiteralPath $Path)) {
    return $events
  }
  foreach ($line in Get-Content -LiteralPath $Path) {
    if (-not $line.Trim()) { continue }
    try {
      $events += ($line | ConvertFrom-Json)
    } catch {
      $events += [pscustomobject]@{ type = "non_json"; text = $line }
    }
  }
  return $events
}

function Get-UsageTokenFields {
  param([array]$Events)

  $hits = @()
  foreach ($event in $Events) {
    if ($event.type -ne "turn.completed" -or -not $event.usage) {
      continue
    }
    foreach ($prop in $event.usage.PSObject.Properties) {
      if ($prop.Name -match "(?i)token|usage") {
        $hits += [pscustomobject]@{
          path = "turn.completed.usage.$($prop.Name)"
          value = $prop.Value
        }
      }
    }
  }
  return $hits
}

function Get-UsageNumber {
  param(
    [array]$Events,
    [string]$Name
  )
  foreach ($event in $Events) {
    if ($event.type -ne "turn.completed" -or -not $event.usage) {
      continue
    }
    $prop = $event.usage.PSObject.Properties[$Name]
    if ($prop -and "$($prop.Value)" -match "^\d+$") {
      return [int64]$prop.Value
    }
  }
  return $null
}

Write-Host "Running Codex raw-output A/B leg..."
Invoke-CodexProofRun -PromptPath $rawPrompt -OutputPath $rawJsonl | Out-Host

Write-Host "Running Codex SAGE-compressed A/B leg..."
Invoke-CodexProofRun -PromptPath $sagePrompt -OutputPath $sageJsonl | Out-Host

$rawEvents = Read-Jsonl -Path $rawJsonl
$sageEvents = Read-Jsonl -Path $sageJsonl
$rawHits = Get-UsageTokenFields -Events $rawEvents
$sageHits = Get-UsageTokenFields -Events $sageEvents

$rawInput = Get-UsageNumber -Events $rawEvents -Name "input_tokens"
$sageInput = Get-UsageNumber -Events $sageEvents -Name "input_tokens"

$saved = $null
$savedUsd = $null
$reduction = $null
if ($null -ne $rawInput -and $null -ne $sageInput -and $rawInput -gt 0) {
  $saved = $rawInput - $sageInput
  $reduction = [math]::Round(($saved / $rawInput) * 100, 2)
  $savedUsd = [math]::Round(($saved / 1000000) * [double]$PricePerMillionInput, 6)
}

$report = [ordered]@{
  provider = "codex-cli"
  model = $(if ($Model.Trim()) { $Model } else { "codex-config-default" })
  price_per_million_input_usd = [double]$PricePerMillionInput
  files = [ordered]@{
    raw_prompt = (Resolve-Path $rawPrompt).Path
    sage_prompt = (Resolve-Path $sagePrompt).Path
    raw_jsonl = (Resolve-Path $rawJsonl).Path
    sage_jsonl = (Resolve-Path $sageJsonl).Path
  }
  raw_token_fields = $rawHits
  sage_token_fields = $sageHits
  raw_input_tokens = $rawInput
  sage_input_tokens = $sageInput
  provider_input_tokens_saved = $saved
  provider_input_reduction_percent = $reduction
  estimated_input_savings_usd = $savedUsd
  note = "If raw_input_tokens or sage_input_tokens is null, this Codex CLI JSON stream did not expose provider usage fields."
}

$report | ConvertTo-Json -Depth 100 | Tee-Object -FilePath $reportPath
Write-Host "Report written to $reportPath"
