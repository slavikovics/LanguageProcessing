import json, statistics as st, sys
def wer_pool(items):
    # corpus-level WER = sum errors / sum ref words
    e = sum(i["wer"]*i["nref"] for i in items); n = sum(i["nref"] for i in items); return e/n
def show(name, R):
    print("==", name)
    c, ng, s = R["cmd"], R["neg"], R["sen"]
    ok = [x for x in c if x["matched"] == x["expected"]]
    print("cmd match", len(ok), "/", len(c), " by voice:", {v: sum(1 for x in c if x["voice"]==v and x["matched"]==x["expected"]) for v in {x['voice'] for x in c}})
    for x in c:
        if x["matched"] != x["expected"]: print("  MISS:", repr(x["text"]), "->", repr(x["hyp"]), x["matched"], "exp", x["expected"], x["voice"])
    fp = [x for x in ng if x["matched"]]
    print("neg FP", len(fp), "/", len(ng))
    for x in ng:
        if x["matched"]: print("  FP:", repr(x["text"]), "->", repr(x["hyp"]), x["matched"])
    print("cmd WER", round(wer_pool(c),3), "neg WER", round(wer_pool(ng),3), "sen WER", round(wer_pool(s),3))
    for v in sorted({x['voice'] for x in s}): print("  sen WER", v, round(wer_pool([x for x in s if x['voice']==v]),3))
    perfect = sum(1 for x in s if x["wer"]==0); print("sen perfect", perfect, "/", len(s))
    for x in s:
        if x["wer"]>0: print("  ERR:", round(x["wer"],2), repr(x["text"]), "->", repr(x["hyp"]))
    allx = c+ng+s
    print("latency ms mean", round(st.mean(x["ms"] for x in allx)), "median", round(st.median(x["ms"] for x in allx)), "rtf", round(sum(x["ms"]/1000 for x in allx)/sum(x["dur"] for x in allx),2), "mean dur", round(st.mean(x["dur"] for x in allx),2))
    for k,l in [("cmd",c),("sen",s)]:
        print(" ", k, "mean ms", round(st.mean(x["ms"] for x in l)), "mean dur", round(st.mean(x["dur"] for x in l),2))
r = json.load(open("stt_en_results.json"))
show("EN small", r["en"])
ss = r["en_stream"]
for k in ("cmd","sen"):
    l=[x for x in ss if x["kind"]==k]
    print("BASE", k, "WER", round(wer_pool(l),3), "ms", round(st.mean(x["ms"] for x in l)), "dur", round(st.mean(x["dur"] for x in l),2), "n", len(l), "perfect", sum(1 for x in l if x['wer']==0))
    if k=="sen":
        for x in l:
            if x["wer"]>0: print("  BASE ERR", round(x['wer'],2), repr(x['hyp']))
print("noise")
for snr, ws in r["noise"].items():
    e=sum(w*n for w,n,_ in ws); n=sum(n for _,n,_ in ws); print(" SNR", snr, "WER", round(e/n,3))
    for w,nn,h in ws:
        if w>0: print("   ", round(w,2), repr(h))
