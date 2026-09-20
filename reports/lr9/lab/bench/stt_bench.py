import json, re, time, wave, random, math, uuid, urllib.request, statistics, sys, io, struct
from array import array
from phrases import *

API = "http://localhost:8000/speech/stt"
SPEECH = "http://localhost:8004/stt"

def multipart(fields, fname, data):
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="audio"; filename="{fname}"\r\nContent-Type: audio/wav\r\n\r\n'.encode() + data + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={b}"

def post(url, fields, data):
    body, ct = multipart(fields, "a.wav", data)
    req = urllib.request.Request(url, data=body, headers={"Content-Type": ct})
    t0 = time.perf_counter()
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    r["wall"] = time.perf_counter() - t0
    return r

def norm(t):
    t = re.sub(r"[^\w\s]", " ", t.lower(), flags=re.UNICODE)
    return t.split()

def wer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]
            d[j] = min(d[j] + 1, d[j-1] + 1, prev + (r[i-1] != h[j-1]))
            prev = cur
    return d[len(h)] / max(1, len(r)), len(r)

def dur(data):
    w = wave.open(io.BytesIO(data)); return w.getnframes() / w.getframerate()

def add_noise(data, snr_db, seed=1):
    rnd = random.Random(seed)
    w = wave.open(io.BytesIO(data))
    n, sr = w.getnframes(), w.getframerate()
    s = array("h"); s.frombytes(w.readframes(n))
    rms = math.sqrt(sum(x*x for x in s) / len(s))
    sd = rms / (10 ** (snr_db / 20))
    out = array("h", (max(-32768, min(32767, int(x + rnd.gauss(0, sd)))) for x in s))
    bio = io.BytesIO()
    with wave.open(bio, "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(out.tobytes())
    return bio.getvalue()

def load(meta_path, base=""):
    m = json.load(open(meta_path))
    for it in m: it["data"] = open(base + it["file"], "rb").read()
    return m

def action_of(kind, idx, lang):
    return (EN_COMMANDS if lang == "en" else RU_COMMANDS)[idx][1]

results = {}
def run_lang(lang, meta):
    R = {"cmd": [], "neg": [], "sen": []}
    for it in meta:
        r = post(API, {"language": lang}, it["data"])
        rec = dict(voice=it["voice"], text=it["text"], hyp=r["transcript"], ms=r["elapsed_ms"], wall=r["wall"],
                   dur=dur(it["data"]), matched=(r.get("matched_command") or {}).get("action"))
        if it["kind"] == "cmd":
            rec["expected"] = action_of("cmd", it["idx"], lang)
        rec["wer"], rec["nref"] = wer(it["text"], r["transcript"])
        R[it["kind"]].append(rec)
        print(lang, it["kind"], it["idx"], it["voice"], round(rec["wer"],2), rec["matched"], flush=True)
    return R

en = load("audio/en/meta.json")
results["en"] = run_lang("en", en)
# stream model (base) on sentences + commands
results["en_stream"] = []
for it in en:
    if it["kind"] in ("sen", "cmd"):
        r = post(SPEECH, {"language": "en", "vad_filter": "true", "use_stream_model": "true"}, it["data"])
        w, n = wer(it["text"], r["transcript"])
        results["en_stream"].append(dict(kind=it["kind"], voice=it["voice"], hyp=r["transcript"], wer=w, nref=n, ms=r["elapsed_ms"], dur=dur(it["data"])))
        print("stream", it["kind"], it["idx"], round(w,2), flush=True)
# noise on amy sentences
results["noise"] = {}
amy = [it for it in en if it["kind"] == "sen" and it["voice"] == "en_US-amy-medium"]
for snr in [20, 10, 5, 0]:
    ws = []
    for it in amy:
        r = post(SPEECH, {"language": "en"}, add_noise(it["data"], snr))
        w, n = wer(it["text"], r["transcript"]); ws.append((w, n, r["transcript"]))
    results["noise"][snr] = ws
    print("noise", snr, statistics.mean(w for w,_,_ in ws), flush=True)
json.dump(results, open("stt_en_results.json", "w"), ensure_ascii=False, indent=1)
