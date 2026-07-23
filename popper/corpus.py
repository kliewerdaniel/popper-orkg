"""corpus.py — load benchmark and frontier corpora into a common shape.

A corpus is a list of "sources", each with an id, title, year, and a list of
claims. This is the substrate every method (compiler + controls) consumes, so
that the ONLY difference between methods is the reasoning, not the input.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class Source:
    id: str
    title: str
    year: int
    claims: List[str] = field(default_factory=list)
    doi: str = ""


@dataclass
class Corpus:
    domain: str
    title: str
    sources: List[Source] = field(default_factory=list)
    # benchmark-only fields (empty for frontier corpora)
    is_false: bool = False
    discovery_year: int = 0
    held_out_paper: Dict = field(default_factory=dict)
    ground_truth_hypothesis: str = ""
    ground_truth_variables: Dict = field(default_factory=dict)

    def all_claims(self) -> List[Dict[str, str]]:
        """Flat list of {claim, source_id, source_title} across the corpus."""
        out = []
        for s in self.sources:
            for c in s.claims:
                out.append({"claim": c, "source_id": s.id, "source_title": s.title})
        return out

    def source_index(self) -> Dict[str, Source]:
        return {s.id: s for s in self.sources}


def load_benchmark(path: str) -> Corpus:
    d = json.load(open(path, encoding="utf-8"))
    sources = [
        Source(
            id=p["id"],
            title=p.get("title", ""),
            year=int(p.get("year", 0)),
            claims=list(p.get("claims", [])),
            doi=p.get("doi", ""),
        )
        for p in d.get("prior_literature", [])
    ]
    return Corpus(
        domain=d["domain"],
        title=d.get("title", d["domain"]),
        sources=sources,
        is_false=bool(d.get("is_false", False)),
        discovery_year=int(d.get("discovery_year", 0)),
        held_out_paper=d.get("held_out_paper", {}),
        ground_truth_hypothesis=d.get("ground_truth_hypothesis", ""),
        ground_truth_variables=d.get("ground_truth_variables", {}),
    )


def load_all_benchmarks(bench_dir: str = "benchmark") -> Dict[str, Corpus]:
    out = {}
    for p in sorted(Path(bench_dir).glob("*.json")):
        c = load_benchmark(str(p))
        out[c.domain] = c
    return out
