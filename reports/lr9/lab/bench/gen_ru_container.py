import json, sys, wave, os
from piper import PiperVoice
items = json.load(sys.stdin)
os.makedirs("/tmp/ru", exist_ok=True)
voices = {}
for it in items:
    v = it["voice"]
    if v not in voices:
        voices[v] = PiperVoice.load(f"/tmp/pv/{v}.onnx")
    path = f"/tmp/ru/{it['name']}.wav"
    with wave.open(path, "wb") as w:
        first = True
        for chunk in voices[v].synthesize(it["text"]):
            if first:
                w.setnchannels(chunk.sample_channels); w.setsampwidth(chunk.sample_width); w.setframerate(chunk.sample_rate); first = False
            w.writeframes(chunk.audio_int16_bytes)
print("ok", len(items))
