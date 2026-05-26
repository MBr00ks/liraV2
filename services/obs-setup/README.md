# OBS + VoiceMeeter Setup for Lira TTS Pipeline

## What This Does

Routes Kokoro TTS audio through OBS for real-time audio processing:
- Compressor (smooth volume)
- EQ (warmth, clarity)
- Noise gate (silence when idle)
- Reverb (spatial presence)

## Requirements

- **OBS Studio 28+** (WebSocket built-in) — needs admin to install
- **VoiceMeeter** (VB-Audio) — free virtual audio cable, needs admin to install
- **OBS WebSocket** — enabled on port 4455

## Step 1: Install Software

Run these in an **Admin PowerShell**:

```powershell
winget install --id OBSProject.OBSStudio --silent --accept-source-agreements
winget install --id VB-Audio.Voicemeeter --silent --accept-source-agreements
```

## Step 2: Enable OBS WebSocket

1. Launch OBS Studio
2. Go to **Tools → WebSocket Server Settings**
3. Check **Enable WebSocket Server**
4. Set **Server Port**: `4455`
5. Set **Password**: `obs_ws_pass` (must match `.env` → `OBS_WS_PASSWORD`)
6. Click **OK**

Config file at `%APPDATA%\obs-studio\plugin_config\obs-websocket\config.json` will be auto-created by this script.

## Step 3: Set Up Audio Routing

### Option A: VoiceMeeter (recommended)

1. Launch VoiceMeeter (Start Menu → VoiceMeeter)
2. Set a virtual input as your TTS destination
3. In Windows sound settings, set your browser (Chrome/Edge/SillyTavern app) output to VoiceMeeter Input
4. In OBS, add Audio Input Capture → select "VoiceMeeter Output"
5. Right-click the source → Advanced Audio Properties → set Audio Monitoring to "Monitor and Output"

### Option B: VB-Cable (simpler, but needs manual download)

1. Download from https://vb-audio.com/Cable/
2. Install (admin required)
3. Set browser audio output to "CABLE Input"
4. In OBS, add Audio Input Capture → "CABLE Output"
5. Set monitoring to "Monitor and Output"

## Step 4: Add Audio Filters in OBS

Right-click your audio source → Filters → add:

1. **Noise Gate** (closes when silent)
   - Close Threshold: -40 dB
   - Open Threshold: -30 dB
   - Attack: 25 ms
   - Release: 150 ms

2. **Compressor**
   - Ratio: 4:1
   - Threshold: -18 dB
   - Attack: 6 ms
   - Release: 60 ms
   - Output Gain: 3 dB

3. **EQ** (presence boost)
   - Low Shelf: 80 Hz, +2 dB
   - Peak: 800 Hz, -2 dB
   - Peak: 3.5 kHz, +3 dB
   - High Shelf: 8 kHz, +2 dB

4. **Reverb** (subtle)
   - Room Size: 25%
   - Decay Time: 500 ms
   - Wet/Dry: 15%

## Step 5: Configure `.env`

Ensure these are set in your `.env`:

```env
OBS_ENABLED=true
OBS_HOST=localhost
OBS_PORT=4455
OBS_PASSWORD=obs_ws_pass
OBS_TTS_SOURCE=Kokoro TTS
```

## Script in `services/obs-setup/`

- `setup-obs.ps1` — creates OBS config files and applies settings
- `test-routing.ps1` — tests the voice-runtime OBS API endpoints

## Verifying It Works

```powershell
# Test OBS WebSocket connection via voice-runtime
curl http://localhost:8000/api/obs/status
# Expected: {"connected": true, "tts_source_exists": true, ...}
```
