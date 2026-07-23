"""ablation.py — systematically remove one compiler component at a time.

The point of an ablation is to prove the compiler's ARCHITECTURE is load-bearing,
not just that the whole system beats weak baselines. We hold everything fixed and
knock out one component per run, then measure the degradation in composite /
grounding / falsifiable-rate / rediscovery-match.

The vendored `popper` package is UNCHANGED. Each ablation is expressed by
composing the existing building blocks differently — a different system prompt, a
restructured corpus view, or a scoring flag — never by editing popper/*.

Components ablated (each keeps the other five intact):

  full                 the real compiler (baseline for the ablation table).
  no_graph_reasoning   claims are flattened into an unlabeled bag with NO source
                       grouping and the cross-source-traversal instruction removed.
                       Tests whether the graph structure (who-said-what, connect
                       ACROSS sources) matters, vs. reasoning over an undifferentiated
                       pile of sentences.
  no_grounding_verif   the LLM grounding audit is switched off (audit=False in
                       score_grounding): source_ids are counted but never checked
                       for whether they actually support the claim. Tests whether
                       provenance VERIFICATION (not just presence) is load-bearing.
  no_gap_detection     the "find a structurally UNSUPPORTED connection that NONE of
                       the sources state directly" instruction is removed; the model
                       is merely asked to state a hypothesis from the claims. Tests
                       whether the gap-seeking objective produces the novelty.
  no_falsifiability    the falsifiable-schema requirement is dropped from the prompt
                       (no forced IV/DV/measurement/falsification/quant-prediction)
                       and testability is not enforced. Tests whether compiling to a
                       falsifiable ARTIFACT (vs. a free-text hypothesis) matters.
  no_lit_synthesis     the corpus is truncated to a SINGLE source, so there is no
                       cross-paper literature synthesis to perform. Tests whether
                       combining multiple papers is load-bearing.

Every ablation's output is scored on the SAME rubric as the full compiler, so the
degradation is directly comparable.
"""
from __future__ import annotations

import random
from dataclasses import replace
from typing import Dict, List

from popper import inference, score
from popper.corpus import Corpus, Source
from popper.schema import Hypothesis, hypothesis_from_dict

# ---------------------------------------------------------------------------
# Ablated system prompts (derived from popper.generate.COMPILER_SYSTEM, with
# exactly one capability removed each).
# ---------------------------------------------------------------------------

_JSON_SHAPE = """Reply with ONLY a JSON object, no prose:
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

# NO GAP DETECTION: remove "structurally unsupported connection ... none state directly"
NO_GAP_SYSTEM = """You are a scientific hypothesis compiler.

You are given a set of established claims, each tagged with the SOURCE it came
from. State a single FALSIFIABLE hypothesis that follows from the claims. You do
NOT need to find an unstated or missing connection; simply express a hypothesis
supported by the claims.

Rules:
- The hypothesis must name an independent variable, a dependent variable, a
  population/system, a measurement, an expected outcome, and a falsification
  condition.
- You MUST make a QUANTITATIVE prediction with a direction and a numeric
  magnitude window, a unit, and a confidence 0..1.
- Each evidence item MUST cite a real source_id from the input. Do NOT invent ids.

""" + _JSON_SHAPE

# NO GRAPH REASONING: claims are an unlabeled bag; no cross-source instruction.
NO_GRAPH_SYSTEM = """You are a scientific hypothesis compiler.

You are given a flat list of established claims (sources not identified). Compile
a single FALSIFIABLE hypothesis from them.

Rules:
- The hypothesis must name an independent variable, a dependent variable, a
  population/system, a measurement, an expected outcome, and a falsification
  condition.
- You MUST make a QUANTITATIVE prediction with a direction and a numeric
  magnitude window, a unit, and a confidence 0..1.
- In the evidence array, cite source_id "corpus" for each claim (individual
  provenance is not available in this mode).

""" + _JSON_SHAPE

# NO FALSIFIABILITY: free-text hypothesis, no forced schema / quant prediction.
NO_FALS_SYSTEM = """You are a scientific hypothesis generator.

You are given established claims, each tagged with its SOURCE. Produce a single
scientific hypothesis connecting concepts across the sources. Write it as you see
fit; a rigid variable/measurement structure is NOT required.

Reply with ONLY a JSON object:
{
  "statement": "...",
  "mechanism": "...optional...",
  "evidence": [{"claim": "...", "source_id": "<real id>", "stance": "supporting"}],
  "source_ids": ["<real id>"]
}"""

# full compiler reuses popper.generate.COMPILER_SYSTEM
from popper.generate import COMPILER_SYSTEM, _format_claims, _attach_titles  # noqa: E402


def _flat_claims_block(corpus: Corpus) -> str:
    lines = [f"- {c['claim']}" for c in corpus.all_claims()]
    return "\n".join(lines)


def _single_source_corpus(corpus: Corpus) -> Corpus:
    """Keep only the source with the most claims (kills literature synthesis)."""
    if not corpus.sources:
        return corpus
    richest = max(corpus.sources, key=lambda s: len(s.claims))
    return replace(corpus, sources=[richest])


def _generate(corpus: Corpus, system: str, user: str, method: str,
              max_tokens: int = 9000, temperature: float = 0.3) -> List[Hypothesis]:
    d = inference.complete_json(system, user, max_tokens=max_tokens,
                                temperature=temperature)
    if not d or not d.get("statement"):
        return []
    h = hypothesis_from_dict(d, method=method)
    return [_attach_titles(h, corpus)]


def run_ablation(corpus: Corpus, component: str, n: int = 3) -> List[Hypothesis]:
    """Generate n hypotheses under a named ablation. Returns unscored hyps."""
    out: List[Hypothesis] = []
    seen = set()

    for i in range(n):
        avoid = ""
        if out:
            avoid = "\n\nDo NOT repeat these already-generated hypotheses:\n" + \
                "\n".join(f"- {h.statement}" for h in out)

        if component == "full":
            claims_block = _format_claims(corpus)
            user = (f"Domain: {corpus.title}\n\nEstablished claims (each tagged "
                    f"with its source):\n{claims_block}\n{avoid}\n\nCompile ONE new "
                    "falsifiable hypothesis that connects concepts across DIFFERENT "
                    "sources. Use only the source_ids shown above.")
            hs = _generate(corpus, COMPILER_SYSTEM, user, "full")

        elif component == "no_graph_reasoning":
            claims_block = _flat_claims_block(corpus)
            user = (f"Domain: {corpus.title}\n\nEstablished claims:\n{claims_block}"
                    f"{avoid}\n\nCompile ONE falsifiable hypothesis from these claims.")
            hs = _generate(corpus, NO_GRAPH_SYSTEM, user, "no_graph_reasoning")

        elif component == "no_gap_detection":
            claims_block = _format_claims(corpus)
            user = (f"Domain: {corpus.title}\n\nEstablished claims (each tagged "
                    f"with its source):\n{claims_block}{avoid}\n\nState ONE "
                    "falsifiable hypothesis supported by these claims.")
            hs = _generate(corpus, NO_GAP_SYSTEM, user, "no_gap_detection")

        elif component == "no_falsifiability":
            claims_block = _format_claims(corpus)
            user = (f"Domain: {corpus.title}\n\nEstablished claims (each tagged "
                    f"with its source):\n{claims_block}{avoid}\n\nState ONE "
                    "hypothesis connecting concepts across the sources.")
            hs = _generate(corpus, NO_FALS_SYSTEM, user, "no_falsifiability")

        elif component == "no_lit_synthesis":
            sub = _single_source_corpus(corpus)
            claims_block = _format_claims(sub)
            user = (f"Domain: {sub.title}\n\nEstablished claims (single source):\n"
                    f"{claims_block}{avoid}\n\nCompile ONE falsifiable hypothesis "
                    "from this source. Use only the source_ids shown above.")
            hs = _generate(sub, COMPILER_SYSTEM, user, "no_lit_synthesis")

        else:
            raise ValueError(f"unknown ablation component: {component}")

        for h in hs:
            if h.statement.lower() in seen:
                continue
            seen.add(h.statement.lower())
            out.append(h)
    return out


ABLATIONS = [
    "full",
    "no_graph_reasoning",
    "no_grounding_verif",   # scoring-side ablation (audit=False), not a generator
    "no_gap_detection",
    "no_falsifiability",
    "no_lit_synthesis",
]


def score_ablation(hyps: List[Hypothesis], corpus: Corpus, component: str,
                   rediscovery: bool = True) -> None:
    """Score in place. no_grounding_verif turns OFF the grounding audit."""
    audit = component != "no_grounding_verif"
    is_bench = bool(corpus.ground_truth_hypothesis)
    for h in hyps:
        score.score_hypothesis(h, corpus, audit=audit,
                               rediscovery=(rediscovery and is_bench))
