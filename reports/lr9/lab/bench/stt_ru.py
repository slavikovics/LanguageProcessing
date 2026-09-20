src = open("stt_bench.py").read().split("results = {}")[0]
exec(src)
def run_lang(lang, meta):
    R = {"cmd": [], "neg": [], "sen": []}
    for it in meta:
        r = post(API, {"language": lang}, it["data"])
        rec = dict(voice=it["voice"], text=it["text"], hyp=r["transcript"], ms=r["elapsed_ms"], wall=r["wall"],
                   dur=dur(it["data"]), matched=(r.get("matched_command") or {}).get("action"))
        if it["kind"] == "cmd": rec["expected"] = RU_COMMANDS[it["idx"]][1]
        rec["wer"], rec["nref"] = wer(it["text"], r["transcript"])
        R[it["kind"]].append(rec)
        print(lang, it["kind"], it["idx"], it["voice"], round(rec["wer"],2), rec["matched"], flush=True)
    return R
ru = load("audio/ru/meta.json")
res = {"ru": run_lang("ru", ru)}
json.dump(res, open("stt_ru_results.json", "w"), ensure_ascii=False, indent=1)
