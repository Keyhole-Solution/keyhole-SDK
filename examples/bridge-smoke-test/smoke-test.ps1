param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$Digest = "sha256:bridge-smoke-test"
)

$ErrorActionPreference = "Stop"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Write-Step {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

$payload = @{
    candidate_digest = $Digest
    payload = @{
        source = "bridge-smoke-test"
        mode   = "powershell"
    }
} | ConvertTo-Json -Depth 5

Write-Host "== Keyhole Bridge Smoke Test ==" -ForegroundColor Green
Write-Host "BASE_URL=$BaseUrl"
Write-Host "DIGEST=$Digest"

Write-Step "health"
$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/healthz"
$health | ConvertTo-Json -Depth 5
Assert-True ($health.status -eq "ok") "Health check failed."
Write-Host "PASS: health" -ForegroundColor Green

Write-Step "identity"
$identity = Invoke-RestMethod -Method Get -Uri "$BaseUrl/identity"
$identity | ConvertTo-Json -Depth 10
Assert-True ($identity.runtime_id -eq "keyhole-test-runtime") "Unexpected runtime_id."
Assert-True ($identity.capabilities -contains "realize") "Missing realize capability."
Assert-True ($identity.capabilities -contains "state") "Missing state capability."
Assert-True ($identity.capabilities -contains "health") "Missing health capability."
Write-Host "PASS: identity" -ForegroundColor Green

Write-Step "initial state"
$initialState = Invoke-RestMethod -Method Get -Uri "$BaseUrl/state"
$initialState | ConvertTo-Json -Depth 10
Assert-True (-not ($initialState.realized_digests -contains $Digest)) "Digest already present before test."
Write-Host "PASS: initial state" -ForegroundColor Green

Write-Step "first realize"
$firstRealize = Invoke-RestMethod -Method Post -Uri "$BaseUrl/realize" -ContentType "application/json" -Body $payload
$firstRealize | ConvertTo-Json -Depth 10
Assert-True ($firstRealize.digest -eq $Digest) "First realize returned wrong digest."
Assert-True ($firstRealize.status -eq "ACCEPT") "First realize did not return ACCEPT."
Write-Host "PASS: first realize" -ForegroundColor Green

Write-Step "replay realize"
$replayRealize = Invoke-RestMethod -Method Post -Uri "$BaseUrl/realize" -ContentType "application/json" -Body $payload
$replayRealize | ConvertTo-Json -Depth 10
Assert-True ($replayRealize.digest -eq $Digest) "Replay returned wrong digest."
Assert-True ($replayRealize.status -eq "ALREADY_REALIZED") "Replay did not return ALREADY_REALIZED."
Write-Host "PASS: replay realize" -ForegroundColor Green

Write-Step "final state"
$finalState = Invoke-RestMethod -Method Get -Uri "$BaseUrl/state"
$finalState | ConvertTo-Json -Depth 10
Assert-True ($finalState.current_digest -eq $Digest) "Final current_digest mismatch."
Assert-True (($finalState.realized_digests | Where-Object { $_ -eq $Digest }).Count -eq 1) "Digest was not present exactly once in realized_digests."
Write-Host "PASS: final state" -ForegroundColor Green

Write-Host ""
Write-Host "Bridge smoke test passed." -ForegroundColor Green