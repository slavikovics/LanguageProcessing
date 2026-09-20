import json, struct, urllib.request, os
from phrases import *
os.makedirs("audio/en", exist_ok=True)
API="http://localhost:8000/speech/tts"
def synth(text, voice):
    req=urllib.request.Request(API, data=json.dumps({"text":text,"voice":voice}).encode(), headers={"Content-Type":"application/json"})
    d=bytearray(urllib.request.urlopen(req, timeout=120).read())
    struct.pack_into("<I", d, 4, len(d)-8); struct.pack_into("<I", d, 40, len(d)-44)
    return bytes(d)
items=[]
for i,(t,a) in enumerate(EN_COMMANDS):
    for v in ["en_US-amy-medium","en_US-ryan-medium"]: items.append(("cmd",i,t,v))
for i,t in enumerate(EN_NEGATIVES):
    for v in ["en_US-amy-medium","en_US-ryan-medium"]: items.append(("neg",i,t,v))
for i,t in enumerate(EN_SENTENCES):
    for v in ["en_US-amy-medium","en_US-ryan-medium","en_GB-alba-medium"]: items.append(("sen",i,t,v))
meta=[]
for kind,i,t,v in items:
    fn=f"audio/en/{kind}{i:02d}_{v}.wav"
    open(fn,"wb").write(synth(t,v))
    meta.append(dict(file=fn,kind=kind,idx=i,text=t,voice=v))
    print(fn, flush=True)
json.dump(meta, open("audio/en/meta.json","w"), ensure_ascii=False, indent=1)
