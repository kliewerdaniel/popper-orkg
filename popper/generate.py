"""generate.py — hypothesis generation methods.

Four methods produce hypotheses from the SAME corpus, so the experiment isolates
the contribution of *structured knowledge compilation* against controls:

  1. compiler   — the real method. Reads the corpus as a set of grounded claims,
                  identifies structurally unsupported connections between
                  established concepts, and compiles falsifiable hypotheses with
                  explicit variables, mechanism, quantitative prediction, and
                  per-claim source_ids.
  2. llm-only   — the ablation. Same model, same request for a falsifiable
                  hypothesis, but WITHOUT the corpus claims (only the domain
                  title). Tests whether the knowledge graph actually helps.
  3. keyword    — the statistical baseline. No LLM reasoning: pick the most
                  frequent co-occurring concept pair across claims and emit a
                  templated hypothesis. Tests whether semantic reasoning beats
                  simple co-occurrence.
  4. random     — the noise floor. Connect two randomly chosen claims. Tests
                  whether the compiler beats randomness.

Every method returns List[Hypothesis]. Controls deliberately produce
structurally weaker artifacts; that asymmetry IS the measurement.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from typing import List

from . import inference
from .corpus import Corpus
from .schema import (
    Evidence,
    Hypothesis,
    QuantitativePrediction,
    hypothesis_from_dict,
)

# ---------------------------------------------------------------------------
# 1. COMPILER (the real method)
# ---------------------------------------------------------------------------

COMPILER_SYSTEM = """You are Popper, a scientific hypothesis compiler.

You are given a set of established claims, each tagged with the SOURCE it came
from. Your job is NOT to summarize. Your job is to identify a structurally
UNSUPPORTED connection between established concepts \u2014 a relationship that the
individual sources each partially support but that NONE of them state directly \u2014
and compile it into a single FALSIFIABLE hypothesis.

Rules:
- Every hypothesis must be falsifiable: it must name an independent variable, a
  dependent variable, a population/system, a measurement, an expected outcome,
  and an explicit falsification condition (what result would prove it wrong).
- You MUST make a QUANTITATIVE prediction: a direction and a numeric magnitude
  window (even if uncertain), with a unit and a confidence 0..1.
- Every element of your reasoning must trace to the provided sources. In the
  "evidence" array, each item MUST cite a real source_id from the input. Do NOT
  invent source_ids. If a step relies on prior knowledge not in the sources,
  mark that evidence item's stance as "contextual" and set source_id to the
  closest real source.
- The hypothesis must be a graph traversal across the sources, not a restatement
  of any single source.

Reply with ONLY a JSON object, no prose:
{
  "statement": "...",
  "independent_variable": "...",
  "dependent_variable": "...",
  "population": "...",
  "measurement": "...",
  "expected_outcome": "...",
  "falsification_condition": "...",
  "mechanism": "... causal chain linking IV to DV ...",
  "prediction": {
    "intervention": "...", "expected_effect": "...",
    "direction": "increase|decrease|change",
    "magnitude_low": <number>, "magnitude_high": <number>,
    "unit": "%|fold|...", "confidence": <0..1>,
    "supporting_count": <int>, "contradictory_count": <int>
  },
  "evidence": [
    {"claim": "...", "source_id": "<real id from input>",
     "stance": "supporting|contradictory|contextual", "quote": ""}
  ],
  "source_ids": ["<real id>", "..."]
}"""


def _format_claims(corpus: Corpus) -> str:
    lines = []
    for s in corpus.sources:
        lines.append(f"SOURCE {s.id} ({s.year}) \u2014 {s.title}")
        for c in s.claims:
            lines.append(f"  - {c}")
    return "\n".join(lines)


def _attach_titles(h: Hypothesis, corpus: Corpus) -> Hypothesis:
    idx = corpus.source_index()
    for e in h.evidence:
        if e.source_id in idx and not e.source_title:
            e.source_title = idx[e.source_id].title
    return h


def compile_hypotheses(corpus: Corpus, n: int = 3, max_tokens: int = 9000) -> List[Hypothesis]:
    """Generate n falsifiable hypotheses via structured compilation."""
    claims_block = _format_claims(corpus)
    out: List[Hypothesis] = []
    seen = set()
    for i in range(n):
        avoid = ""
        if out:
            avoid = "\n\nDo NOT repeat these already-generated hypotheses:\n" + \
                "\n".join(f"- {h.statement}" for h in out)
        user = (
            f"Domain: {corpus.title}\n\n"
            f"Established claims (each tagged with its source):\n{claims_block}\n"
            f"{avoid}\n\n"
            "Compile ONE new falsifiable hypothesis that connects concepts across "
            "DIFFERENT sources. Use only the source_ids shown above."
        )
        d = inference.complete_json(COMPILER_SYSTEM, user, max_tokens=max_tokens,
                                    temperature=0.3)
        if not d or not d.get("statement"):
            print(f"  [compiler] hypothesis {i+1}: empty/failed")
            continue
        h = hypothesis_from_dict(d, method="compiler")
        if h.statement.lower() in seen:
            continue
        seen.add(h.statement.lower())
        out.append(_attach_titles(h, corpus))
    return out


# ---------------------------------------------------------------------------
# 2. LLM-ONLY (ablation: no corpus grounding)
# ---------------------------------------------------------------------------

LLM_ONLY_SYSTEM = """You are a scientific hypothesis generator.

Produce a single FALSIFIABLE hypothesis in the given domain. Include an
independent variable, dependent variable, population, measurement, expected
outcome, falsification condition, mechanism, and a quantitative prediction.

You have NO source documents \u2014 rely on your own knowledge. In "evidence", cite
what you can, using source_id "prior-knowledge" for anything from your own
training rather than a provided document.

Reply with ONLY the same JSON object schema as a hypothesis compiler would."""


def llm_only_hypotheses(corpus: Corpus, n: int = 3, max_tokens: int = 9000) -> List[Hypothesis]:
    out: List[Hypothesis] = []
    seen = set()
    for i in range(n):
        avoid = ""
        if out:
            avoid = "\n\nAvoid repeating:\n" + "\n".join(f"- {h.statement}" for h in out)
        user = (
            f"Domain: {corpus.title}\n{avoid}\n\n"
            "Generate ONE falsifiable hypothesis in this domain."
        )
        d = inference.complete_json(LLM_ONLY_SYSTEM, user, max_tokens=max_tokens,
                                    temperature=0.4)
        if not d or not d.get("statement"):
            continue
        h = hypothesis_from_dict(d, method="llm-only")
        if h.statement.lower() in seen:
            continue
        seen.add(h.statement.lower())
        out.append(h)
    return out


# ---------------------------------------------------------------------------
# 3. KEYWORD CO-OCCURRENCE (statistical baseline, no LLM)
# ---------------------------------------------------------------------------

_STOP = set("""a an the of to in on for and or with without by is are was were be been
being that this these those which who whom whose it its as at from into than then
can could may might will would should shle we they i you he she them our their via
using use used within across between not no such most more less over under about
each per both same other any all some new using based across during more measure
measured measurable study studies paper papers result results effect effects""".split())


def _keywords(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{3,}", text.lower())
    return [w for w in words if w not in _STOP]


def keyword_hypotheses(corpus: Corpus, n: int = 3) -> List[Hypothesis]:
    """Emit templated hypotheses from the most frequent co-occurring concepts."""
    claims = corpus.all_claims()
    # count concept co-occurrence within claims
    pair_counts: Counter = Counter()
    concept_source: dict = {}
    for c in claims:
        kws = list(dict.fromkeys(_keywords(c["claim"])))[:8]
        for kw in kws:
            concept_source.setdefault(kw, set()).add(c["source_id"])
        for a in range(len(kws)):
            for b in range(a + 1, len(kws)):
                pair = tuple(sorted((kws[a], kws[b])))
                pair_counts[pair] += 1
    out: List[Hypothesis] = []
    for (w1, w2), _cnt in pair_counts.most_common(n):
        stmt = (f"Increasing {w1} produces a measurable change in {w2}.")
        src_ids = sorted((concept_source.get(w1, set()) | concept_source.get(w2, set())))
        ev = [Evidence(claim=f"co-occurrence of '{w1}' and '{w2}'",
                       source_id=sid, stance="contextual") for sid in src_ids[:4]]
        h = Hypothesis(
            id=Hypothesis.make_id(stmt, "keyword"),
            statement=stmt,
            independent_variable=w1,
            dependent_variable=w2,
            mechanism="",  # deliberately absent: co-occurrence has no mechanism
            evidence=ev,
            source_ids=src_ids,
            method="keyword",
            notes="keyword co-occurrence baseline; no mechanism, no prediction",
        )
        out.append(h)
    return out


# ---------------------------------------------------------------------------
# 4. RANDOM TRAVERSAL (noise floor, no LLM)
# ---------------------------------------------------------------------------

def random_hypotheses(corpus: Corpus, n: int = 3, seed: int = 0) -> List[Hypothesis]:
    rng = random.Random(seed)
    claims = corpus.all_claims()
    out: List[Hypothesis] = []
    if len(claims) < 2:
        return out
    for _ in range(n):
        a, b = rng.sample(claims, 2)
        stmt = f"There is a relationship between: '{a['claim']}' and '{b['claim']}'."
        ev = [
            Evidence(claim=a["claim"], source_id=a["source_id"], stance="contextual"),
            Evidence(claim=b["claim"], source_id=b["source_id"], stance="contextual"),
        ]
        h = Hypothesis(
            id=Hypothesis.make_id(stmt, "random") + f"-{rng.randint(0,9999)}",
            statement=stmt,
            mechanism="",
            evidence=ev,
            source_ids=sorted({a["source_id"], b["source_id"]}),
            method="random",
            notes="random claim-pair traversal; noise floor",
        )
        out.append(h)
    return out


METHODS = {
    "compiler": compile_hypotheses,
    "llm-only": llm_only_hypotheses,
    "keyword": keyword_hypotheses,
    "random": random_hypotheses,
}
