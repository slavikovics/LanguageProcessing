import json, re, struct, time, statistics, urllib.request

API = "http://localhost:8000/speech/tts"

TEXT_S = "Transformers process sequences in parallel using self-attention."
TEXT_M = ("We propose a novel neural architecture for machine translation that replaces recurrence "
          "with multi-head self-attention. The model achieves state-of-the-art results on the WMT benchmark "
          "while requiring significantly less time to train.")
ABSTRACT = (
    "Recent advances in deep learning have transformed natural language processing. "
    "In this paper we study the problem of information retrieval over large collections of scientific articles. "
    "We represent each document as a weighted vector of terms and rank documents by cosine similarity to the query. "
    "The proposed indexing module updates the vocabulary incrementally, which avoids rebuilding the whole index. "
    "Experiments on a crawled collection show that the vector model reaches higher precision than boolean retrieval. "
    "We also compare several term weighting schemes and analyse their sensitivity to document length. "
    "Finally, we discuss limitations of the approach and outline directions for future work, "
    "including dense neural representations and cross-lingual search."
)

def synth(text, voice="en_US-amy-medium", rate=1.0):
    body = json.dumps({"text": text, "voice": voice, "rate": rate}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first = None
    data = b""
    with urllib.request.urlopen(req, timeout=120) as r:
        while True:
            chunk = r.read(4096)
            if not chunk:
                break
            if first is None:
                first = time.perf_counter() - t0
            data += chunk
    total = time.perf_counter() - t0
    sr = struct.unpack("<I", data[24:28])[0]
    dur = (len(data) - 44) / 2 / sr
    return dict(ttfb=first, total=total, dur=dur, size=len(data), sr=sr)

def chunk_text(text, target=120, mx=240):
    normalized = re.sub(r"\s+", " ", text).strip()
    sentences = re.findall(r"[^.!?\n]+[.!?]+(?=\s|$)|[^.!?\n]+$", normalized) or [normalized]
    chunks, cur = [], ""
    for raw in sentences:
        s = raw.strip()
        if not s: continue
        if len(s) > mx:
            if cur: chunks.append(cur); cur = ""
            for i in range(0, len(s), mx): chunks.append(s[i:i+mx])
            continue
        cand = f"{cur} {s}" if cur else s
        if len(cand) > target and cur:
            chunks.append(cur); cur = s
        else:
            cur = cand
    if cur: chunks.append(cur)
    return chunks

VOICES = ["en_US-amy-medium","en_US-lessac-medium","en_US-hfc_female-medium","en_US-kristin-medium",
          "en_US-ryan-medium","en_US-hfc_male-medium","en_US-joe-medium",
          "en_GB-alba-medium","en_GB-jenny_dioco-medium","en_GB-alan-medium"]
out = {}

# A. voices: cold (first call) + 3 warm
out["voices"] = {}
for v in VOICES:
    cold = synth(TEXT_M, v)
    warm = [synth(TEXT_M, v) for _ in range(3)]
    out["voices"][v] = dict(cold_total=cold["total"], cold_ttfb=cold["ttfb"],
        warm_total=statistics.mean(w["total"] for w in warm), warm_ttfb=statistics.mean(w["ttfb"] for w in warm),
        dur=statistics.mean(w["dur"] for w in warm))
    print(v, out["voices"][v], flush=True)

# B. length scaling (amy, warm)
out["length"] = []
for name, txt in [("S", TEXT_S), ("M", TEXT_M), ("L", ABSTRACT[:700]), ("XL", ABSTRACT*2)]:
    runs = [synth(txt) for _ in range(3)]
    out["length"].append(dict(name=name, chars=len(txt), ttfb=statistics.mean(r["ttfb"] for r in runs),
        total=statistics.mean(r["total"] for r in runs), dur=statistics.mean(r["dur"] for r in runs)))
    print(out["length"][-1], flush=True)

# C. rate
out["rate"] = []
base = None
for rate in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
    runs = [synth(TEXT_M, rate=rate) for _ in range(3)]
    d = statistics.mean(r["dur"] for r in runs)
    if rate == 1.0: base = d
    out["rate"].append(dict(rate=rate, dur=d, total=statistics.mean(r["total"] for r in runs)))
for r in out["rate"]: r["ratio"] = r["dur"] / base
print(out["rate"], flush=True)

# D. whole text vs chunked (first audio latency), 3 runs
txt = ABSTRACT * 3
chunks = chunk_text(txt)
whole = [synth(txt[:5000]) for _ in range(3)]
first_chunk = [synth(chunks[0]) for _ in range(3)]
out["chunking"] = dict(chars=len(txt[:5000]), n_chunks=len(chunks),
    chunk_lens=[len(c) for c in chunks],
    whole_total=statistics.mean(w["total"] for w in whole), whole_dur=statistics.mean(w["dur"] for w in whole),
    whole_ttfb=statistics.mean(w["ttfb"] for w in whole),
    first_chunk_total=statistics.mean(w["total"] for w in first_chunk),
    first_chunk_dur=statistics.mean(w["dur"] for w in first_chunk))
# steady state: does synth of chunk k+1 finish before chunk k finished playing? (all chunks)
per = [synth(c) for c in chunks]
out["chunking"]["gaps"] = [max(0, per[i+1]["total"] - per[i]["dur"]) for i in range(len(per)-1)]
out["chunking"]["chunk_totals"] = [p["total"] for p in per]
out["chunking"]["chunk_durs"] = [p["dur"] for p in per]
print(out["chunking"], flush=True)
json.dump(out, open("tts_results.json","w"), indent=1)
