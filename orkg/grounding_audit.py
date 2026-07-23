"""grounding_audit.py — provenance statistics over generated hypotheses.

The success criterion "hypotheses remain fully traceable to ORKG evidence"
requires more than the scalar grounding score. This module classifies EVERY
evidence item of EVERY hypothesis into one of three provenance tiers and rolls
them up per method / per domain:

  fully_grounded    source_id is a REAL id present in the corpus AND the LLM
                    grounding audit confirmed the source supports the claim.
  partially_grounded source_id is real/in-corpus but the audit was inconclusive,
                    OR the audit was not run (score without audit).
  unsupported       source_id is missing, a placeholder ("prior-knowledge",
                    "model", ...), OR a hallucinated id NOT in the corpus, OR the
                    audit judged the source does NOT support the claim.

We re-use popper's exact grounding logic (corpus.source_index + the same audit
prompt) so these statistics are consistent with the scores the pipeline assigns.
"""
from __future__ import annotations

from typing import Dict, List

from popper import inference
from popper.corpus import Corpus
from popper.schema import Hypothesis
from popper.score import GROUNDING_AUDIT_SYSTEM


def audit_hypothesis_evidence(h: Hypothesis, corpus: Corpus,
                              audit: bool = True) -> List[Dict]:
    """Return per-evidence provenance verdicts for one hypothesis."""
    idx = corpus.source_index()
    valid_ids = set(idx.keys())
    rows: List[Dict] = []

    auditable = []  # (row_index, evidence)
    for e in h.evidence:
        real = e.is_grounded() and e.source_id in valid_ids
        row = {
            "claim": e.claim,
            "source_id": e.source_id,
            "in_corpus": e.source_id in valid_ids,
            "is_grounded_id": e.is_grounded(),
            "tier": "unsupported",
            "audit_supported": None,
        }
        rows.append(row)
        if real and audit:
            auditable.append((len(rows) - 1, e))
        elif real and not audit:
            row["tier"] = "partially_grounded"  # real id, no verification

    if audit and auditable:
        blocks = []
        for i, (_ri, e) in enumerate(auditable, 1):
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
        for i, (ri, _e) in enumerate(auditable, 1):
            v = verdicts.get(i)
            rows[ri]["audit_supported"] = v
            if v is True:
                rows[ri]["tier"] = "fully_grounded"
            elif v is False:
                rows[ri]["tier"] = "unsupported"
            else:
                rows[ri]["tier"] = "partially_grounded"
    return rows


def summarize(all_rows: List[Dict]) -> Dict:
    tiers = {"fully_grounded": 0, "partially_grounded": 0, "unsupported": 0}
    for r in all_rows:
        tiers[r["tier"]] += 1
    total = sum(tiers.values()) or 1
    return {
        "n_evidence": sum(tiers.values()),
        "fully_grounded": tiers["fully_grounded"],
        "partially_grounded": tiers["partially_grounded"],
        "unsupported": tiers["unsupported"],
        "fully_grounded_rate": round(tiers["fully_grounded"] / total, 4),
        "partially_grounded_rate": round(tiers["partially_grounded"] / total, 4),
        "unsupported_rate": round(tiers["unsupported"] / total, 4),
        "hallucinated_ids": sum(1 for r in all_rows
                                if r["is_grounded_id"] and not r["in_corpus"]),
    }
