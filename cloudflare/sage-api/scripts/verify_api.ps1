param(
  [string]$BaseUrl = "https://sage.api.marketingstudios.in"
)

$ErrorActionPreference = "Stop"

$keyBody = @{
  display_name = "PsYcGoD"
  username = "PsYcGoD"
  public_profile = $true
  privacy_max = 1
  scope = "founder-test"
} | ConvertTo-Json

$keyResponse = Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/keys" -ContentType "application/json" -Body $keyBody
$apiKey = [string]$keyResponse.api_key

$telemetryBody = @{
  schema_version = "1.0"
  event_type = "command_completed"
  installation_id = "local-founder-test"
  workspace_hash = "workspace_demo_hash"
  run_hash = "run_demo_hash"
  command_kind = "test"
  command_family = "verification"
  privacy_level = 1
  success = $true
  exit_code = 0
  prediction_score = 0.08
  agent_count = 4
  metrics = @{
    original_tokens = 100000
    compressed_tokens = 12000
    saved_tokens = 88000
    compression_rate = 88.0
    duration_ms = 2800
  }
} | ConvertTo-Json -Depth 8

$headers = @{
  Authorization = "Bearer $apiKey"
  "X-SAGE-Idempotency-Key" = "founder-test-2026-07-04-0001"
}

$telemetryResponse = Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/telemetry" -Headers $headers -ContentType "application/json" -Body $telemetryBody
$proof = Invoke-RestMethod -Uri "$BaseUrl/v1/proof"

[pscustomobject]@{
  base_url = $BaseUrl
  created_key_id = $keyResponse.key_id
  api_key_redacted = ($apiKey.Substring(0, [Math]::Min(24, $apiKey.Length)) + "...redacted")
  telemetry_ok = $telemetryResponse.ok
  duplicate = $telemetryResponse.duplicate
  event_id = $telemetryResponse.event_id
  proof_totals = $proof.totals
  public_contributors = $proof.public_contributors
} | ConvertTo-Json -Depth 8
