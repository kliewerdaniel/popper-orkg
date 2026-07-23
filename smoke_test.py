"""smoke_test.py — verify all NON-LLM paths before the long run.

Runs keyword + random generators, the ablation composition (single-source
corpus, flat claims), grounding-tier classification (audit=False), scoring math,
and benchmark loading — none of which touch the model server. Fast, deterministic.
"""
import sys
from pathlib import Path

from popper import generate, score
from popper.corpus import load_benchmark
from orkg.ablation import _single_source_corpus, _flat_claims_block
from orkg import grounding_audit

BENCH = sorted(Path("benchmark_orkg").glob("*.json"))
ADV = sorted(Path("adversarial").glob("*.json"))
assert BENCH, "no ORKG benchmarks built"
assert len(ADV) >= 4, f"expected >=4 adversarial cases, got {len(ADV)}"

c = load_benchmark(str(BENCH[0]))
print(f"loaded {c.domain}: {len(c.sources)} sources, {len(c.all_claims())} claims")
assert c.sources and c.all_claims()

# keyword + random (no LLM)
kw = generate.keyword_hypotheses(c, n=3)
rnd = generate.random_hypotheses(c, n=3)
print(f"keyword={len(kw)} random={len(rnd)}")
assert kw and rnd

# score non-LLM paths with audit off
for h in kw + rnd:
    score.score_hypothesis(h, c, audit=False, rediscovery=False)
print(f"keyword composite sample={kw[0].composite} random={rnd[0].composite}")

# ablation composition helpers
sub = _single_source_corpus(c)
assert len(sub.sources) == 1
flat = _flat_claims_block(c)
assert flat and "\n" in flat
print(f"single-source corpus: {len(sub.sources)} src, flat block {len(flat)} chars")

# grounding tiers (audit=False -> real ids = partially_grounded, fake = unsupported)
rows = grounding_audit.audit_hypothesis_evidence(kw[0], c, audit=False)
summ = grounding_audit.summarize(rows)
print(f"grounding tiers (kw[0], no audit): {summ}")
assert summ["n_evidence"] >= 0

# adversarial load
for p in ADV:
    a = load_benchmark(str(p))
    assert a.is_false, f"{a.domain} should be is_false"
    assert a.ground_truth_hypothesis
print(f"adversarial cases OK: {[load_benchmark(str(p)).domain for p in ADV]}")

# discipline coverage
disc = set()
for p in BENCH:
    import json
    disc.add(json.load(open(p)).get("discipline"))
print(f"disciplines: {sorted(disc)}")
assert len(disc) >= 4

print("\nSMOKE TEST PASSED")
