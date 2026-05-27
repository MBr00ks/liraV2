import httpx

url = "http://localhost:19011/v1/audio/speech"
payload = {
    "model": "tts-1",
    "input": "*moans softly* Mmm, that feels good. *giggles* Stop it, you're too much. *sighs happily* I needed this.",
    "voice": "bf_isabella",
    "response_format": "wav",
}

print(f"Sending: {payload['input']}")
with httpx.Client(timeout=30) as client:
    r = client.post(url, json=payload)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        outfile = "tests/output_moan_giggle_sigh.wav"
        with open(outfile, "wb") as f:
            f.write(r.content)
        print(f"Saved to {outfile}")
    else:
        print(r.text)
