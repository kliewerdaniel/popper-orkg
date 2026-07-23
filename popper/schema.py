"""schema.py — the falsifiable hypothesis schema.

This is the heart of Popper. The previous iterations (SDC, SQC) generated
*questions*. Popper generates *hypotheses* — and a hypothesis is only admitted
if it is structurally falsifiable. A linguistically convincing sentence is not
enough; every hypothesis must carry the machinery a scientist needs to try to
kill it.

A hypothesis is a compiled artifact. Like a compiler emits an executable that
must pass tests, Popper emits a Hypothesis that must pass validation:
grounding, novelty, testability, and (where available) expert agreement.

    Literature -> Knowledge Compiler -> Hypothesis -> Validation

The schema below is deliberately strict. Missing an independent variable, a
falsification condition, or a source id is not a stylistic lapse — it is a
compile error. `Hypothesis.validate()` returns the list of such errors.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Evidence:
    """A single traceable claim -> source link.

    `source_id` is the non-negotiable field. If a claim cannot name the source
    it was derived from, it is a prior-knowledge fill-in, not evidence. That
    distinction is the entire credibility of the project.
    """

    claim: str
    source_id: str                 # e.g. "paperA", "orkg:R12345", "doi:10.1038/..."
    source_title: str = ""
    stance: str = "supporting"     # supporting | contradictory | contextual
    quote: str = ""                # optional verbatim span from the source

    def is_grounded(self) -> bool:
        return bool(self.source_id) and self.source_id.lower() not in {
            "", "none", "n/a", "prior", "prior-knowledge", "model", "unknown",
        }


@dataclass
class QuantitativePrediction:
    """The major upgrade over 'X may influence Y'.

    Forces a directional, measurable prediction with a magnitude window and a
    confidence — even when uncertain. 'Blocking IL-6 reduces hippocampal
    inflammatory markers by >20%' rather than 'investigate inflammation'.
    """

    intervention: str              # what you change
    expected_effect: str           # measurable change in the DV
    direction: str = "increase"    # increase | decrease | change | no-change
    magnitude_low: Optional[float] = None   # e.g. 15.0  (percent, fold, etc.)
    magnitude_high: Optional[float] = None  # e.g. 30.0
    unit: str = ""                 # "%", "fold", "mmHg", ...
    confidence: float = 0.0        # 0..1
    supporting_count: int = 0
    contradictory_count: int = 0

    def has_number(self) -> bool:
        return self.magnitude_low is not None or self.magnitude_high is not None


@dataclass
class Hypothesis:
    """A falsifiable scientific hypothesis — the compiled artifact."""

    id: str
    statement: str                             # one-sentence hypothesis

    # --- Testability core (the six fields a scientist needs) ---
    independent_variable: str = ""
    dependent_variable: str = ""
    population: str = ""                        # population / system studied
    measurement: str = ""                       # how the DV is measured
    expected_outcome: str = ""
    falsification_condition: str = ""           # what result would refute it

    mechanism: str = ""                         # proposed causal chain
    prediction: Optional[QuantitativePrediction] = None
    evidence: List[Evidence] = field(default_factory=list)

    # --- Scores (filled by validation passes; -1 = not yet scored) ---
    novelty: float = -1.0
    grounding: float = -1.0
    testability: float = -1.0
    expert_agreement: float = -1.0
    composite: float = -1.0

    # --- Provenance ---
    source_ids: List[str] = field(default_factory=list)
    method: str = "compiler"                    # compiler | random | llm-only | keyword
    notes: str = ""

    # ---- Structural validation: falsifiability as a compile check ----
    REQUIRED_TEXT = (
        "statement",
        "independent_variable",
        "dependent_variable",
        "measurement",
        "expected_outcome",
        "falsification_condition",
        "mechanism",
    )

    def validate(self) -> List[str]:
        """Return a list of compile errors. Empty list == falsifiable."""
        errors: List[str] = []
        for f_ in self.REQUIRED_TEXT:
            if not str(getattr(self, f_, "")).strip():
                errors.append(f"missing:{f_}")
        if self.prediction is None:
            errors.append("missing:prediction")
        elif not self.prediction.has_number():
            errors.append("prediction:no-magnitude")
        grounded = [e for e in self.evidence if e.is_grounded()]
        if not grounded:
            errors.append("evidence:ungrounded (no source_ids)")
        return errors

    def is_falsifiable(self) -> bool:
        return not self.validate()

    def grounding_rate(self) -> float:
        """Fraction of evidence items that carry a verifiable source_id."""
        if not self.evidence:
            return 0.0
        grounded = sum(1 for e in self.evidence if e.is_grounded())
        return grounded / len(self.evidence)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["falsifiable"] = self.is_falsifiable()
        d["validation_errors"] = self.validate()
        return d

    @staticmethod
    def make_id(statement: str, method: str = "compiler") -> str:
        h = hashlib.sha1(f"{method}:{statement}".encode("utf-8")).hexdigest()[:10]
        return f"H-{h}"


# ---------- (de)serialization helpers tolerant of model drift ----------

def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def prediction_from_dict(d: Optional[Dict[str, Any]]) -> Optional[QuantitativePrediction]:
    if not d or not isinstance(d, dict):
        return None
    return QuantitativePrediction(
        intervention=str(d.get("intervention", "")).strip(),
        expected_effect=str(d.get("expected_effect", "")).strip(),
        direction=str(d.get("direction", "increase")).strip() or "increase",
        magnitude_low=_num(d.get("magnitude_low")),
        magnitude_high=_num(d.get("magnitude_high")),
        unit=str(d.get("unit", "")).strip(),
        confidence=float(_num(d.get("confidence")) or 0.0),
        supporting_count=int(_num(d.get("supporting_count")) or 0),
        contradictory_count=int(_num(d.get("contradictory_count")) or 0),
    )


def evidence_from_list(items: Any) -> List[Evidence]:
    out: List[Evidence] = []
    if not isinstance(items, list):
        return out
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append(Evidence(
            claim=str(it.get("claim", "")).strip(),
            source_id=str(it.get("source_id", "")).strip(),
            source_title=str(it.get("source_title", "")).strip(),
            stance=str(it.get("stance", "supporting")).strip() or "supporting",
            quote=str(it.get("quote", "")).strip(),
        ))
    return out


def hypothesis_from_dict(d: Dict[str, Any], method: str = "compiler") -> Hypothesis:
    statement = str(d.get("statement", "")).strip()
    ev = evidence_from_list(d.get("evidence"))
    source_ids = [str(s) for s in d.get("source_ids", []) if str(s).strip()]
    if not source_ids:
        source_ids = sorted({e.source_id for e in ev if e.is_grounded()})
    hid = str(d.get("id") or Hypothesis.make_id(statement, method))
    return Hypothesis(
        id=hid,
        statement=statement,
        independent_variable=str(d.get("independent_variable", "")).strip(),
        dependent_variable=str(d.get("dependent_variable", "")).strip(),
        population=str(d.get("population", "")).strip(),
        measurement=str(d.get("measurement", "")).strip(),
        expected_outcome=str(d.get("expected_outcome", "")).strip(),
        falsification_condition=str(d.get("falsification_condition", "")).strip(),
        mechanism=str(d.get("mechanism", "")).strip(),
        prediction=prediction_from_dict(d.get("prediction")),
        evidence=ev,
        source_ids=source_ids,
        method=method,
        notes=str(d.get("notes", "")).strip(),
    )


def dump_hypotheses(hyps: List[Hypothesis], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([h.to_dict() for h in hyps], fh, indent=2, ensure_ascii=False)
