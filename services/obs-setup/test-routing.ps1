param(
    [string]$BaseUrl = "http://localhost:8000"
)

$Endpoint = "$BaseUrl/api/obs"
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Test-OBSEndpoint($path, $method="GET", $body=$null) {
    $url = "$Endpoint$path"
    try {
        if ($method -eq "GET") {
            $resp = Invoke-RestMethod -Uri $url -Method Get -ErrorAction Stop
        } else {
            $resp = Invoke-RestMethod -Uri $url -Method Post -Body $body -ErrorAction Stop
        }
        Write-Host "  ✓ $method $path" -ForegroundColor Green
        return $resp
    } catch {
        Write-Host "  ✗ $method $path — $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

Write-Host "=== OBS Routing Test ===" -ForegroundColor Cyan
Write-Host ""

# 1. Status check
$status = Test-OBSEndpoint "/status"
if ($status) {
    Write-Host "    connected: $($status.connected)" -ForegroundColor $(if ($status.connected) {$Green} else {$Yellow})
    Write-Host "    tts_source: $($status.tts_source_exists)" -ForegroundColor $(if ($status.tts_source_exists) {$Green} else {$Yellow})
    Write-Host "    filters: $($status.filters_active -join ', ')"
}

if ($status.connected) {
    Write-Host ""
    Write-Host "--- Volume ---" -ForegroundColor Cyan
    $vol = Test-OBSEndpoint "/source/volume?source=Kokoro%20TTS"
    if ($vol) { Write-Host "    volume: $($vol.volume_db) dB" }

    Write-Host ""
    Write-Host "--- Mute Toggle ---" -ForegroundColor Cyan
    Test-OBSEndpoint "/source/mute?source=Kokoro%20TTS" -method POST

    Write-Host ""
    Write-Host "--- Filters ---" -ForegroundColor Cyan
    $filters = Test-OBSEndpoint "/filters?source=Kokoro%20TTS"
    if ($filters) {
        foreach ($f in $filters.filters) {
            Write-Host "    $($f.name): $(if($f.enabled){'enabled'}else{'disabled'})"
        }
    }

    Write-Host ""
    Write-Host "--- Scenes ---" -ForegroundColor Cyan
    $scenes = Test-OBSEndpoint "/scenes"
    if ($scenes) {
        foreach ($s in $scenes.scenes) {
            Write-Host "    $s"
        }
    }
}

Write-Host ""
if ($status.connected) {
    Write-Host "=== All checks passed ===" -ForegroundColor Green
    Write-Host "TTS audio routing through OBS is operational."
} else {
    Write-Host "=== OBS not connected ===" -ForegroundColor Yellow
    Write-Host "Make sure:"
    Write-Host "  1. OBS Studio is running"
    Write-Host "  2. WebSocket is enabled (Tools → WebSocket Server Settings)"
    Write-Host "  3. voice-runtime is running (check: curl http://localhost:8000/api/obs/status)"
}
