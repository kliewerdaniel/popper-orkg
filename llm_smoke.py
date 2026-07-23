"""llm_smoke.py — ONE real compiler generate + full score, end-to-end.

Confirms the LLM path (compile_hypotheses -> score_hypothesis with audit +
rediscovery) works against the live model before the multi-hour run. Also does
one ablation generate to confirm the ablated prompts parse.
"""
import time
from pathlib import Path
from popper import generate, score
from popper.corpus import load_benchmark
from orkg.ablation import run_ablation, score_ablation

p = sorted(Path("benchmark_orkg").glob("*.json"))[0]
c = load_benchmark(str(p))
print(f"domain: {c.domain} sources={len(c.sources)} claims={len(c.all_claims())}")

t0 = time.time()
hyps = generate.compile_hypotheses(c, n=1)
print(f"compiler generated {len(hyps)} in {time.time()-t0:.0f}s")
assert hyps, "compiler returned nothing"
h = hyps[0]
print("statement:", h.statement[:120])
print("IV:", h.independent_variable[:60], "| DV:", h.dependent_variable[:60])
print("evidence source_ids:", [e.source_id for e in h.evidence])

t0 = time.time()
score.score_hypothesis(h, c, audit=True, rediscovery=True)
print(f"scored in {time.time()-t0:.0f}s: nov={h.novelty} grnd={h.grounding} "
      f"test={h.testability} exp={h.expert_agreement} comp={h.composite} "
      f"fals={h.is_falsifiable()}")

# one ablation to confirm ablated prompt parses
t0 = time.time()
ab = run_ablation(c, "no_gap_detection", n=1)
score_ablation(ab, c, "no_gap_detection")
print(f"ablation no_gap_detection: {len(ab)} hyps in {time.time()-t0:.0f}s "
      f"comp={ab[0].composite if ab else 'NONE'}")

print("\nLLM SMOKE PASSED")
