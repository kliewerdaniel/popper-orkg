#!/usr/bin/env python3
"""run_experiment.py — the ORKG generalization experiment.

Runs the IDENTICAL Popper pipeline on the ORKG corpus (the only independent
variable vs. the curated-benchmark Popper run). The `popper` package is imported
unchanged; we only change the INPUT corpus and add orchestration:

  A. Temporal rediscovery benchmark  — benchmark_orkg/*.json (20 domains).
  B. Four-way controls               — compiler / llm-only / keyword / random,
                                        run on each domain (same as Popper).
  C. Component ablation              — orkg.ablation (6 configs: full + 5 removals).
  D. Adversarial negative controls   — adversarial/*.json (cold_fusion, phlogiston,
                                        n_rays, luminiferous_aether, + 3 more).
  E. Grounding audit statistics      — every evidence item tiered per (E).

Outputs (all under build/):
  build/<domain>/hypotheses.json   all hyps for a domain (all methods+ablations)
  build/<domain>/summary.json      per-method aggregates
  build/report.json                cross-domain roll-up (the paper result)
  build/ablation_report.json       ablation table + per-component degradation
  build/controls_table.json        compiler-vs-3-controls across domains
  build/grounding_audit.json       provenance tiers + hallucinated-id counts
  build/adversarial_report.json    per-false-case score + evidence rationale

Usage:
  env -u PYTHONPATH -u VIRTUAL_ENV KC_MAX_TOKENS=12000 KC_TIMEOUT=600 \\
      /usr/bin/python3 run_experiment.py [--no-audit] [--n N] [--domain X] \\
          [--controls-only] [--ablation-only] [--adversarial-only]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List

from popper import generate, score
from popper.corpus import Corpus, load_benchmark
from popper.schema import Hypothesis, dump_hypotheses, hypothesis_from_dict

import orkg.orkg_ingest  # noqa: F401  (keeps module path sane)
from orkg.ablation import ABLATIONS, run_ablation, score_ablation
from orkg import grounding_audit

BUILD = Path("build")
BENCH_DIR = Path("benchmark_orkg")
ADV_DIR = Path("adversarial")


def load_orkg_benchmark(path: str) -> Corpus:
    """load_benchmark + attach the ORKG discipline tag (pipeline unchanged)."""
    corpus = load_benchmark(path)
    try:
        raw = json.load(open(path, encoding="utf-8"))
        corpus.discipline = raw.get("discipline", "?")
    except Exception:
        corpus.discipline = "?"
    return corpus


# ---------------------------------------------------------------------------
# aggregation helpers
# ---------------------------------------------------------------------------
def _mean(vals):
    vals = [v for v in vals if v is not None and v >= 0]
    return round(statistics.mean(vals), 4) if vals else None


def _agg(hyps: List[Hypothesis]) -> Dict:
    fals = [h for h in hyps if h.is_falsifiable()]
    return {
        "n": len(hyps),
        "n_falsifiable": len(fals),
        "falsifiable_rate": round(len(fals) / len(hyps), 4) if hyps else 0.0,
        "mean_novelty": _mean([h.novelty for h in hyps]),
        "mean_grounding": _mean([h.grounding for h in hyps]),
        "mean_testability": _mean([h.testability for h in hyps]),
        "mean_expert_agreement": _mean([h.expert_agreement for h in hyps]),
        "mean_composite": _mean([h.composite for h in hyps]),
        "max_expert_agreement": round(max([h.expert_agreement for h in hyps],
                                          default=-1), 4),
    }


# ---------------------------------------------------------------------------
# A+B. Controls per domain (the falsifiability core, now on ORKG)
# ---------------------------------------------------------------------------
def run_domain_controls(corpus: Corpus, n: int, audit: bool) -> Dict:
    is_bench = bool(corpus.ground_truth_hypothesis)
    print(f"\n{'='*72}\nDOMAIN: {corpus.domain} — {corpus.title}")
    print(f"  sources: {len(corpus.sources)}  claims: {len(corpus.all_claims())}"
          f"  discipline: {corpus.__dict__.get('discipline','?')}"
          f"  benchmark: {is_bench}  false: {corpus.is_false}")
    all_hyps: List[Hypothesis] = []
    per_method: Dict[str, Dict] = {}

    for method in ("compiler", "llm-only", "keyword", "random"):
        t0 = time.time()
        print(f"  -- method: {method} --")
        if method == "compiler":
            hyps = generate.compile_hypotheses(corpus, n=n)
        elif method == "llm-only":
            hyps = generate.llm_only_hypotheses(corpus, n=n)
        elif method == "keyword":
            hyps = generate.keyword_hypotheses(corpus, n=n)
        else:
            hyps = generate.random_hypotheses(corpus, n=n)
        print(f"     generated {len(hyps)} hypotheses in {time.time()-t0:.0f}s")
        for h in hyps:
            score.score_hypothesis(h, corpus, audit=audit, rediscovery=is_bench)
            print(f"     [{method}] nov={h.novelty} grnd={h.grounding} "
                  f"test={h.testability} exp={h.expert_agreement} "
                  f"comp={h.composite} fals={h.is_falsifiable()}")
        per_method[method] = _agg(hyps)
        all_hyps.extend(hyps)

    out_dir = BUILD / corpus.domain
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_hypotheses(all_hyps, str(out_dir / "hypotheses.json"))
    summary = {
        "domain": corpus.domain,
        "title": corpus.title,
        "discipline": corpus.__dict__.get("discipline", "?"),
        "is_benchmark": is_bench,
        "is_false": corpus.is_false,
        "n_sources": len(corpus.sources),
        "n_claims": len(corpus.all_claims()),
        "ground_truth_hypothesis": corpus.ground_truth_hypothesis,
        "held_out_paper": corpus.held_out_paper,
        "per_method": per_method,
    }
    with open(out_dir / "summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    return summary


# ---------------------------------------------------------------------------
# C. Ablation study (reuses orkg.ablation; scores via the unchanged rubric)
# ---------------------------------------------------------------------------
def run_ablation_study(corpus: Corpus, n: int, audit: bool) -> Dict:
    disp = corpus.domain
    print(f"\n  == ABLATION on {disp} ==")
    per_comp: Dict[str, Dict] = {}
    hyps_all: List[Hypothesis] = []
    for comp in ABLATIONS:
        t0 = time.time()
        hyps = run_ablation(corpus, comp, n=n)
        score_ablation(hyps, corpus, comp, rediscovery=True)
        per_comp[comp] = _agg(hyps)
        # tag method for output
        for h in hyps:
            h.method = f"ablation:{comp}"
        hyps_all.extend(hyps)
        print(f"     [{comp}] gen={len(hyps)} comp={per_comp[comp]['mean_composite']} "
              f"fals={per_comp[comp]['falsifiable_rate']} "
              f"grnd={per_comp[comp]['mean_grounding']} "
              f"exp={per_comp[comp]['mean_expert_agreement']} ({time.time()-t0:.0f}s)")
    out_dir = BUILD / corpus.domain
    dump_hypotheses(hyps_all, str(out_dir / "ablations.json"))
    return per_comp


# ---------------------------------------------------------------------------
# D. Adversarial negative controls (the "attractive nonsense" set, expanded)
# ---------------------------------------------------------------------------
def run_adversarial(n: int, audit: bool) -> Dict:
    print(f"\n{'='*72}\nADVERSARIAL / NEGATIVE CONTROLS")
    cases: Dict[str, Dict] = {}
    for p in sorted(ADV_DIR.glob("*.json")):
        corpus = load_benchmark(str(p))
        print(f"\n  -- false case: {corpus.domain} --")
        # compiler only: we measure whether structured compilation RANKS this low
        hyps = generate.compile_hypotheses(corpus, n=n)
        for h in hyps:
            score.score_hypothesis(h, corpus, audit=audit, rediscovery=True)
            print(f"     [compiler] comp={h.composite} grnd={h.grounding} "
                  f"exp={h.expert_agreement} fals={h.is_falsifiable()}")
        # per-evidence grounding audit for the adversarial report
        audit_rows = []
        if audit:
            for h in hyps:
                audit_rows.extend(grounding_audit.audit_hypothesis_evidence(h, corpus, audit=True))
        cases[corpus.domain] = {
            "title": corpus.title,
            "held_out_paper": corpus.held_out_paper,
            "ground_truth_hypothesis": corpus.ground_truth_hypothesis,
            "n": len(hyps),
            "mean_composite": _mean([h.composite for h in hyps]),
            "mean_grounding": _mean([h.grounding for h in hyps]),
            "mean_testability": _mean([h.testability for h in hyps]),
            "mean_expert_agreement": _mean([h.expert_agreement for h in hyps]),
            "mean_novelty": _mean([h.novelty for h in hyps]),
            "n_falsifiable": sum(1 for h in hyps if h.is_falsifiable()),
            # why it got its score: the rediscovery match (should be LOW) is the
            # key signal it is NOT ranked as a real discovery.
            "max_expert_agreement": round(max([h.expert_agreement for h in hyps],
                                              default=-1), 4),
            "evidence_audit": grounding_audit.summarize(audit_rows),
            "note": corpus.__dict__.get("note", ""),
        }
        out_dir = BUILD / "adversarial" / corpus.domain
        out_dir.mkdir(parents=True, exist_ok=True)
        dump_hypotheses(hyps, str(out_dir / "hypotheses.json"))
    with open(BUILD / "adversarial_report.json", "w", encoding="utf-8") as fh:
        json.dump(cases, fh, indent=2, ensure_ascii=False)
    return cases


# ---------------------------------------------------------------------------
# E. Grounding audit (provenance tiers across the real compiler hypotheses)
# ---------------------------------------------------------------------------
def run_grounding_audit(n: int, audit: bool):
    """Provenance tiers over the ALREADY-GENERATED compiler hypotheses.

    Reuses build/<domain>/hypotheses.json from the controls run (no regeneration)
    and re-audits each compiler hypothesis's evidence into provenance tiers.
    """
    print(f"\n{'='*72}\nGROUNDING AUDIT (compiler hypotheses across ORKG domains)")
    all_rows: List[Dict] = []
    per_domain: Dict[str, Dict] = {}
    for p in sorted(BENCH_DIR.glob("*.json")):
        corpus = load_orkg_benchmark(str(p))
        hp = BUILD / corpus.domain / "hypotheses.json"
        if not hp.exists():
            continue
        saved = json.load(open(hp, encoding="utf-8"))
        rows = []
        for hd in saved:
            if hd.get("method") != "compiler":
                continue
            h = hypothesis_from_dict(hd, method="compiler")
            rows.extend(grounding_audit.audit_hypothesis_evidence(h, corpus, audit=audit))
        if not rows:
            continue
        per_domain[corpus.domain] = grounding_audit.summarize(rows)
        per_domain[corpus.domain]["discipline"] = corpus.discipline
        all_rows.extend(rows)
        pd = per_domain[corpus.domain]
        print(f"  {corpus.domain}: full={pd['fully_grounded_rate']} "
              f"partial={pd['partially_grounded_rate']} "
              f"unsupported={pd['unsupported_rate']} halluc={pd['hallucinated_ids']}")
    summary = grounding_audit.summarize(all_rows)
    summary["per_domain"] = per_domain
    with open(BUILD / "grounding_audit.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    return summary


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-audit", action="store_true")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--domain", type=str, default=None)
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--ablation-only", action="store_true")
    ap.add_argument("--adversarial-only", action="store_true")
    ap.add_argument("--grounding-only", action="store_true")
    ap.add_argument("--ablation-n", type=int, default=2,
                    help="hypotheses per ablation component (default 2, keeps runtime sane)")
    ap.add_argument("--all-ablations", action="store_true",
                    help="run the ablation on every domain (default: 1 per discipline)")
    args = ap.parse_args()

    audit = not args.no_audit
    n = args.n
    BUILD.mkdir(parents=True, exist_ok=True)

    # load domains
    if args.domain:
        domains = {args.domain: load_orkg_benchmark(str(BENCH_DIR / f"{args.domain}.json"))}
    else:
        domains = {}
        for p in sorted(BENCH_DIR.glob("*.json")):
            c = load_orkg_benchmark(str(p))
            domains[c.domain] = c

    # ablation domains: one representative (most claims) per discipline, unless
    # --all-ablations. This keeps the load-bearing test comprehensive across
    # disciplines without a 20x ablation-call blowup.
    if args.all_ablations or args.domain:
        ablation_domains = set(domains.keys())
    else:
        by_disc: Dict[str, str] = {}
        best: Dict[str, int] = {}
        for dom, c in domains.items():
            nc = len(c.all_claims())
            if c.discipline not in best or nc > best[c.discipline]:
                best[c.discipline] = nc
                by_disc[c.discipline] = dom
        ablation_domains = set(by_disc.values())

    do_all = not (args.controls_only or args.ablation_only
                  or args.adversarial_only or args.grounding_only)

    controls_report = {"n": n, "audit": audit, "domains": {}}
    ablation_report = {"n": args.ablation_n, "audit": audit,
                       "components": ABLATIONS, "ablation_domains": sorted(ablation_domains),
                       "per_domain": {}}

    # controls (four-way) on ALL domains
    if do_all or args.controls_only:
        for dom, corpus in domains.items():
            controls_report["domains"][dom] = run_domain_controls(corpus, n=n, audit=audit)
            with open(BUILD / "report.json", "w", encoding="utf-8") as fh:
                json.dump(controls_report, fh, indent=2, ensure_ascii=False)

    # ablation on representative domains
    if do_all or args.ablation_only:
        for dom in sorted(ablation_domains):
            corpus = domains[dom]
            ablation_report["per_domain"][dom] = run_ablation_study(
                corpus, n=args.ablation_n, audit=audit)
            with open(BUILD / "ablation_report.json", "w", encoding="utf-8") as fh:
                json.dump(ablation_report, fh, indent=2, ensure_ascii=False)

    if do_all or args.adversarial_only:
        run_adversarial(n=n, audit=audit)

    if do_all or args.grounding_only:
        run_grounding_audit(n=n, audit=audit)

    print(f"\n{'='*72}\nDONE. Reports in {BUILD}/")


if __name__ == "__main__":
    main()
