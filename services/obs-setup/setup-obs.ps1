param(
    [switch]$NoInstall,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$OBS_SYSTEM = "$env:ProgramFiles\obs-studio\bin\64bit\obs64.exe"
$OBS_USER = "$env:LOCALAPPDATA\Programs\obs-studio\bin\64bit\obs64.exe"
$VM_DIR = "$env:ProgramFiles\VB\Voicemeeter"
$OBS_APPDATA = "$env:APPDATA\obs-studio"

$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Cyan = "Cyan"

function Write-Status($msg, $color) {
    Write-Host "[$(Get-Date -Format HH:mm:ss)] $msg" -ForegroundColor $color
}

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if ($Help) {
    Write-Host @"
OBS + VoiceMeeter Setup for Lira TTS Pipeline

USAGE:
  .\setup-obs.ps1              Full setup (install + config)
  .\setup-obs.ps1 -NoInstall   Config only (skip software install)
  .\setup-obs.ps1 -Help        This message

STEPS:
  1. Install OBS Studio + VoiceMeeter (admin required)
  2. Enable OBS WebSocket on port 4455
  3. Create OBS profile 'Lira TTS'
  4. Create scene with Kokoro TTS audio source
  5. Configure voice-runtime .env
"@
    exit 0
}

Write-Status "=== Lira OBS Setup ===" $Cyan

# --- Step 1: Check / Install Software ---
if (-not $NoInstall) {
    $obsInstalled = (Test-Path $OBS_SYSTEM) -or (Test-Path $OBS_USER)
    $vmInstalled = Test-Path $VM_DIR

    if (-not $obsInstalled) {
        if (Test-Admin) {
            Write-Status "Installing OBS Studio..." $Yellow
            winget install --id OBSProject.OBSStudio --silent --accept-source-agreements 2>&1
            Write-Status "OBS installed" $Green
        } else {
            Write-Status "OBS not installed. Run this script as Admin, or install manually:" $Red
            Write-Host "  winget install --id OBSProject.OBSStudio --silent --accept-source-agreements"
        }
    } else {
        Write-Status "OBS already installed" $Green
    }

    if (-not $vmInstalled) {
        if (Test-Admin) {
            Write-Status "Installing VoiceMeeter..." $Yellow
            winget install --id VB-Audio.Voicemeeter --silent --accept-source-agreements 2>&1
            Write-Status "VoiceMeeter installed" $Green
        } else {
            Write-Status "VoiceMeeter not installed. Run this script as Admin, or install manually:" $Red
            Write-Host "  winget install --id VB-Audio.Voicemeeter --silent --accept-source-agreements"
        }
    } else {
        Write-Status "VoiceMeeter already installed" $Green
    }
} else {
    Write-Status "Skipping software install (-NoInstall)" $Yellow
}

# --- Step 2: Create OBS WebSocket config ---
$wsDir = "$OBS_APPDATA\plugin_config\obs-websocket"
$null = New-Item -ItemType Directory -Path $wsDir -Force
$wsConfig = @{
    version         = 1
    server_enabled  = $true
    server_port     = 4455
    server_password = "obs_ws_pass"
    server_debug    = $false
} | ConvertTo-Json
Set-Content -Path "$wsDir\config.json" -Value $wsConfig -Encoding UTF8
Write-Status "OBS WebSocket config created (port 4455, password: obs_ws_pass)" $Green

# --- Step 3: Create OBS profile ---
$profileDir = "$OBS_APPDATA\basic\profiles\Lira TTS"
$null = New-Item -ItemType Directory -Path $profileDir -Force
$basicIni = @"
[General]
Name=Lira TTS
ScaleType=bicubic
FPSStr=30
FPSType=Common
FPSCommon=30
BaseRes=1920x1080
OutputRes=1920x1080

[Audio]
SampleRate=48000
ChannelSetup=stereo
DesktopDevice=Default
DesktopDevice2=Default
AuxDevice1=VoiceMeeter Output
AuxDevice2=Default
AuxDevice3=Default
AuxDevice4=Default
MeterDecayRate=1
MeterHoldTime=500
"@
Set-Content -Path "$profileDir\basic.ini" -Value $basicIni -Encoding UTF8
Write-Status "OBS profile 'Lira TTS' created" $Green

# --- Step 4: Create scene collection ---
$sceneDir = "$OBS_APPDATA\basic\scenes"
$null = New-Item -ItemType Directory -Path $sceneDir -Force

# Minimal scene with Kokoro TTS audio source
$sceneConfig = @{
    sources = @(
        @{
            id = "wasapi_input_capture"
            name = "Kokoro TTS"
            versioned_id = "wasapi_input_capture"
            settings = @{
                device_id = "VoiceMeeter Output"
                use_device_timing = $false
            }
            mixers = 1
            volume = 1.0
            enabled = $true
            monitoring_type = 1
            sync = 0
            flags = 0
            private_settings = @{}
        }
    )
} | ConvertTo-Json -Depth 10

Set-Content -Path "$sceneDir\Lira TTS.json" -Value $sceneConfig -Encoding UTF8
Write-Status "Scene collection 'Lira TTS' created" $Green

# --- Step 5: Update .env ---
$envFile = "$PSScriptRoot\..\..\.env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -notmatch "OBS_ENABLED") {
        $envContent += @"

# OBS Audio Processing Pipeline
OBS_ENABLED=true
OBS_HOST=localhost
OBS_PORT=4455
OBS_PASSWORD=obs_ws_pass
OBS_TTS_SOURCE=Kokoro TTS
"@
        Set-Content -Path $envFile -Value $envContent -Encoding UTF8
        Write-Status "OBS settings added to .env" $Green
    } else {
        Write-Status ".env already has OBS settings" $Yellow
    }
} else {
    Write-Status ".env not found at $envFile — add OBS settings manually" $Red
}

# --- Summary ---
Write-Status @"

=== Setup Complete ===" $Cyan

if (-not (Test-Admin)) {
    Write-Status "NOTE: Software may not have been installed (not running as Admin)" $Yellow
    Write-Status "Run with Admin rights to install OBS + VoiceMeeter automatically" $Yellow
}

Write-Status @"
Next steps (manual):
  1. Launch OBS Studio
  2. Tools → WebSocket Server Settings → verify enabled on port 4455
  3. Launch VoiceMeeter (Start Menu)
  4. Set browser audio output to VoiceMeeter Input (Windows sound settings)
  5. In OBS, add Audio Input Capture → VoiceMeeter Output → name it 'Kokoro TTS'
  6. Add filters (see README.md)
  7. Verify: curl http://localhost:8000/api/obs/status
"@ $Cyan
