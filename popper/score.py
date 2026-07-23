"""score.py — validate hypotheses like a compiler validates an executable.

Four scores, each in [0,1], combined into a composite:

  grounding    = fraction of evidence items with a verifiable source_id,
                 discounted by an LLM audit that checks whether the cited
                 source actually supports the claim (catches "articulate
                 autocomplete" that cites a real id for an unsupported claim).
  testability  = structural falsifiability: how many of the required fields
                 (IV, DV, measurement, expected outcome, falsification
                 condition, mechanism, quantitative prediction) are present and
                 non-trivial. Computed WITHOUT the model \u2014 it is objective.
  novelty      = distance from the corpus's existing claims (token-overlap
                 proxy) times an LLM check for "is this already directly stated
                 in the sources". 1.0 = no known direct connection.
  expert_agree = only for the rediscovery benchmark: semantic match between the
                 hypothesis and the held-out ground-truth hypothesis. For
                 frontier runs it stays -1 (not applicable) and is dropped from
                 the composite.

  composite    = geometric-style product of the applicable scores. A zero in any
                 dimension tanks the composite \u2014 by design. A beautifully written
                 but ungrounded hypothesis should NOT score well.
"""
from __future__ import annotations

import re
from typing import List, Optional

from . import inference
from .corpus import Corpus
from .schema import Hypothesis

_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{2,}")


def _tokens(text: str) -> set:
    return set(w.lower() for w in _WORD.findall(text or ""))


# ---------------------------------------------------------------------------
# testability  (objective, no model)
# ---------------------------------------------------------------------------

def score_testability(h: Hypothesis) -> float:
    checks = [
        bool(h.independent_variable.strip()),
        bool(h.dependent_variable.strip()),
        bool(h.measurement.strip()),
        bool(h.expected_outcome.strip()),
        bool(h.falsification_condition.strip()),
        bool(h.mechanism.strip()),
        h.prediction is not None and h.prediction.has_number(),
    ]
    return round(sum(checks) / len(checks), 4)


# ---------------------------------------------------------------------------
# grounding  (source_ids + optional LLM audit)
# ---------------------------------------------------------------------------

GROUNDING_AUDIT_SYSTEM = """You are a grounding auditor. You are given several
(claim, cited-source) pairs, numbered. For each, decide whether the source text
actually supports the claim, or whether the claim is a plausible-sounding
fill-in not backed by the source.

Reply with ONLY JSON mapping each number to a verdict:
{"results": [{"n": 1, "supported": true, "confidence": 0.9}, ...]}"""


def score_grounding(h: Hypothesis, corpus: Corpus, audit: bool = True) -> float:
    if not h.evidence:
        return 0.0
    idx = corpus.source_index()
    valid_ids = set(idx.keys())
    total = len(h.evidence)

    # First pass (objective): keep only evidence whose source_id is REAL.
    auditable = []  # (position, evidence)
    grounded = 0.0
    for pos, e in enumerate(h.evidence):
        if not e.is_grounded() or e.source_id not in valid_ids:
            continue  # ungrounded or hallucinated provenance -> no credit
        if not audit:
            grounded += 1.0
        else:
            auditable.append((pos, e))

    if not audit:
        return round(grounded / total, 4)
    if not auditable:
        return round(grounded / total, 4)

    # Second pass (one batched LLM audit for the whole hypothesis).
    blocks = []
    for i, (_pos, e) in enumerate(auditable, 1):
        src = idx[e.source_id]
        src_text = f"{src.title}: " + "; ".join(src.claims)
        blocks.append(f"{i}. CLAIM: {e.claim}\n   SOURCE {src.id}: {src_text}")
    d = inference.complete_json(
        GROUNDING_AUDIT_SYSTEM,
        "Audit each pair:\n\n" + "\n\n".join(blocks),
        max_tokens=4000, temperature=0.0,
    )
    verdicts = {}
    for r in (d.get("results") or []):
        try:
            verdicts[int(r.get("n"))] = r.get("supported")
        except (TypeError, ValueError):
            continue
    for i in range(1, len(auditable) + 1):
        v = verdicts.get(i)
        if v is True:
            grounded += 1.0
        elif v is False:
            grounded += 0.0
        else:
            grounded += 0.5  # inconclusive -> partial credit
    return round(grounded / total, 4)


# ---------------------------------------------------------------------------
# novelty  (distance from existing claims + LLM "already stated?" check)
# ---------------------------------------------------------------------------

NOVELTY_SYSTEM = """You judge scientific novelty. Given a hypothesis and the set
of established claims it was built from, decide whether the hypothesis is ALREADY
DIRECTLY STATED by one of the claims (an obvious rediscovery) or whether it
asserts a NEW connection not directly present in any single claim.

Reply with ONLY JSON: {"already_stated": true|false, "confidence": 0..1}"""


def score_novelty(h: Hypothesis, corpus: Corpus, audit: bool = True) -> float:
    claim_tokens = [_tokens(c["claim"]) for c in corpus.all_claims()]
    ht = _tokens(h.statement + " " + h.mechanism)
    if not ht:
        return 0.0
    # max Jaccard overlap with any single existing claim (proxy for "already there")
    max_overlap = 0.0
    for ct in claim_tokens:
        if not ct:
            continue
        inter = len(ht & ct)
        union = len(ht | ct)
        if union:
            max_overlap = max(max_overlap, inter / union)
    distance = 1.0 - max_overlap
    if not audit:
        return round(distance, 4)
    claims_block = "\n".join(f"- {c['claim']}" for c in corpus.all_claims())
    d = inference.complete_json(
        NOVELTY_SYSTEM,
        f"Hypothesis: {h.statement}\nMechanism: {h.mechanism}\n\nEstablished claims:\n{claims_block}",
        max_tokens=2000, temperature=0.0,
    )
    if d.get("already_stated") is True:
        return round(min(distance, 0.2), 4)   # cap novelty if it's a rediscovery
    return round(distance, 4)


# ---------------------------------------------------------------------------
# expert agreement / rediscovery match  (benchmark only)
# ---------------------------------------------------------------------------

REDISCOVERY_SYSTEM = """You compare a generated hypothesis against the actual
historical discovery it should have reconstructed. Decide how closely the
generated hypothesis captures the SAME core scientific claim (same independent
variable, same dependent variable, same asserted relationship).

Reply with ONLY JSON:
{"match": 0..1, "captures_iv": true|false, "captures_dv": true|false,
 "captures_relationship": true|false, "reason": "one sentence"}"""


def score_rediscovery(h: Hypothesis, corpus: Corpus, max_tokens: int = 3000) -> dict:
    if not corpus.ground_truth_hypothesis:
        return {"match": -1.0}
    gt = corpus.ground_truth_hypothesis
    gv = corpus.ground_truth_variables or {}
    user = (
        f"GENERATED hypothesis:\n{h.statement}\n"
        f"IV: {h.independent_variable}\nDV: {h.dependent_variable}\n"
        f"Mechanism: {h.mechanism}\n\n"
        f"ACTUAL historical discovery (ground truth):\n{gt}\n"
        f"Ground-truth IV: {gv.get('independent_variable','')}\n"
        f"Ground-truth DV: {gv.get('dependent_variable','')}\n"
    )
    d = inference.complete_json(REDISCOVERY_SYSTEM, user, max_tokens=max_tokens,
                                temperature=0.0)
    try:
        d["match"] = float(d.get("match", 0.0))
    except (TypeError, ValueError):
        d["match"] = 0.0
    return d


# ---------------------------------------------------------------------------
# composite
# ---------------------------------------------------------------------------

def composite_score(h: Hypothesis) -> float:
    """Quality composite: geometric mean of novelty x grounding x testability.

    Any zero tanks it (by design) — a beautifully written but ungrounded
    hypothesis must not score well. Rediscovery match (expert_agreement) is a
    SEPARATE benchmark axis, not folded in here: a hypothesis can be excellent
    quality without reconstructing one specific historical discovery.
    """
    dims = [h.novelty, h.grounding, h.testability]
    dims = [max(0.0, min(1.0, d)) for d in dims if d >= 0]
    if not dims:
        return 0.0
    prod = 1.0
    for d in dims:
        prod *= d
    return round(prod ** (1.0 / len(dims)), 4)  # geometric mean


def score_hypothesis(
    h: Hypothesis,
    corpus: Corpus,
    audit: bool = True,
    rediscovery: bool = False,
) -> Hypothesis:
    h.testability = score_testability(h)
    h.grounding = score_grounding(h, corpus, audit=audit)
    h.novelty = score_novelty(h, corpus, audit=audit)
    if rediscovery and corpus.ground_truth_hypothesis:
        r = score_rediscovery(h, corpus)
        h.expert_agreement = r.get("match", -1.0)
        if r.get("reason"):
            h.notes = (h.notes + " | rediscovery: " + r["reason"]).strip(" |")
    h.composite = composite_score(h)
    return h
