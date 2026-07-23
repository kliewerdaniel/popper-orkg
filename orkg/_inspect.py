import json
idx = json.load(open("build_orkg/index.json"))
probs = idx["problems"]; papers = idx["papers"]; contribs = idx["contribs"]; res = idx.get("resources",{})
ranked = sorted(probs.items(), key=lambda kv: len(kv[1].get("papers",[])), reverse=True)[:6]
for pid,p in ranked:
    print(pid, "|", p.get("label"), "| papers:", len(p.get("papers",[])))
print("=== sample papers of top problem ===")
top = ranked[0][1]["papers"][:3]
for pidx in top:
    pp = papers.get(pidx,{})
    print("PAPER", pidx, "label:", (pp.get("label","") or "")[:80], "contribs:", pp.get("contributions"))
    for cid in pp.get("contributions",[])[:2]:
        c = contribs.get(cid,{})
        print("  contrib:", c.get("label",""), "| desc:", (c.get("description","") or "")[:60])
        for st in c.get("statements",[])[:15]:
            print("     stmt:", st)
