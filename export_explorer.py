#!/usr/bin/env python3
"""export_explorer.py — turn build/ artifacts into explorer/data/ files.

Reads the ORKG experiment outputs and writes compact JSON the Next.js explorer
imports at build time:

  explorer/data/report.json          controls report (per-domain four-way)
  explorer/data/hypotheses.json      {domain: [hypothesis, ...]} (controls)
  explorer/data/ablation.json        ablation report (per-domain per-component)
  explorer/data/grounding.json       provenance tiers per domain + overall
  explorer/data/adversarial.json     per-false-case scores + evidence audit
  explorer/data/meta.json            disciplines + counts for the overview
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

BUILD = Path("build")
DATA = Path("explorer/data")


def _load(p: Path, default):
    return json.load(open(p, encoding="utf-8")) if p.exists() else default


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    report = _load(BUILD / "report.json", {"n": 0, "audit": True, "domains": {}})
    json.dump(report, open(DATA / "report.json", "w"), indent=2, ensure_ascii=False)

    # per-domain hypotheses (controls) + ablation hypotheses
    by_domain = {}
    for dom in report.get("domains", {}):
        hp = BUILD / dom / "hypotheses.json"
        if hp.exists():
            by_domain[dom] = json.load(open(hp, encoding="utf-8"))
    json.dump(by_domain, open(DATA / "hypotheses.json", "w"), indent=2, ensure_ascii=False)

    ablation = _load(BUILD / "ablation_report.json",
                     {"components": [], "per_domain": {}})
    json.dump(ablation, open(DATA / "ablation.json", "w"), indent=2, ensure_ascii=False)

    grounding = _load(BUILD / "grounding_audit.json", {})
    json.dump(grounding, open(DATA / "grounding.json", "w"), indent=2, ensure_ascii=False)

    adversarial = _load(BUILD / "adversarial_report.json", {})
    json.dump(adversarial, open(DATA / "adversarial.json", "w"), indent=2, ensure_ascii=False)

    # discipline roll-up for the overview
    by_disc = defaultdict(lambda: {"domains": 0, "composite": [], "grounding": [],
                                   "rediscovery": [], "falsifiable": []})
    for dom, d in report.get("domains", {}).items():
        disc = d.get("discipline", "?")
        cm = d.get("per_method", {}).get("compiler", {})
        b = by_disc[disc]
        b["domains"] += 1
        for key, mk in (("composite", "mean_composite"), ("grounding", "mean_grounding"),
                        ("rediscovery", "max_expert_agreement"),
                        ("falsifiable", "falsifiable_rate")):
            v = cm.get(mk)
            if v is not None and v >= 0:
                b[key].append(v)
    disc_summary = {}
    for disc, b in by_disc.items():
        def mean(xs):
            return round(sum(xs) / len(xs), 4) if xs else None
        disc_summary[disc] = {
            "domains": b["domains"],
            "mean_composite": mean(b["composite"]),
            "mean_grounding": mean(b["grounding"]),
            "mean_rediscovery": mean(b["rediscovery"]),
            "mean_falsifiable_rate": mean(b["falsifiable"]),
        }

    meta = {
        "n_domains": len(report.get("domains", {})),
        "n_adversarial": len(adversarial),
        "disciplines": disc_summary,
        "n_hypotheses": sum(len(v) for v in by_domain.values()),
        "ablation_domains": ablation.get("ablation_domains", []),
        "audit": report.get("audit", True),
    }
    json.dump(meta, open(DATA / "meta.json", "w"), indent=2, ensure_ascii=False)

    print(f"exported: {len(by_domain)} domains, {meta['n_hypotheses']} hypotheses, "
          f"{len(adversarial)} adversarial, {len(disc_summary)} disciplines, "
          f"ablation on {len(ablation.get('per_domain', {}))} domains")


if __name__ == "__main__":
    main()
