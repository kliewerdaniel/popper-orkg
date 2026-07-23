"""orkg_ingest.py — stream-parse the ORKG RDF dump into a compact, queryable index.

The dump (rdf-export-orkg.nt) is ~6.3M N-Triples. We walk it ONCE, in bounded memory,
and build:

  predicates : P-code -> human label            (e.g. P34 -> "evaluation")
  resources  : uri    -> {label, description, types}
  papers     : uri    -> {label, contributions:[contrib_uri], problems:[prob_uri]}
  contribs   : uri    -> {label, description, paper, statements:[(pred_label, object)]}
  problems   : uri    -> {label, papers:[paper_uri]}

A "statement" is a triple whose subject is a Contribution and whose predicate is a
P-code; the object is either a resource label or a literal. We resolve P-codes to
their labels so each Contribution becomes a readable scientific claim-set.

This is the scale layer: instead of grepping 897MB repeatedly, we pay the parse cost
once and get a JSON index we can query freely. Local-first, stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

DUMP = sys.argv[1] if len(sys.argv) > 1 else "~/Downloads/rdf-export-orkg.nt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "build/orkg/index.json"

NS = "http://orkg.org/orkg/"
PREFIXES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://www.w3.org/2002/07/owl#": "owl:",
    "http://www.w3.org/2001/XMLSchema#": "xsd:",
    "http://schema.org/": "schema:",
}

RE_SUBJ = re.compile(r'^<([^>]+)>\s+<([^>]+)>\s+(.*)\s+\.\s*$')
RE_LIT = re.compile(r'^"(.*?)"(?:\^\^<[^>]+>|@[a-z]+)?\s*$', re.S)


def _short(uri: str) -> str:
    if uri.startswith(NS):
        return uri[len(NS):]
    for full, short in PREFIXES.items():
        if uri.startswith(full):
            return short + uri[len(full):]
    return uri


def _obj(text: str) -> str:
    """Return the object as a short form: resource id, or literal text."""
    text = text.strip()
    if text.startswith("<"):
        return _short(text[1:-1])
    m = RE_LIT.match(text)
    return m.group(1) if m else text


def _is_uri(text: str) -> bool:
    return text.strip().startswith("<")


def parse(dump_path: str) -> Dict:
    predicates: Dict[str, str] = {}
    resources: Dict[str, dict] = defaultdict(lambda: {"label": "", "description": "", "types": []})
    papers: Dict[str, dict] = defaultdict(lambda: {"label": "", "contributions": [], "problems": [], "year": None, "field": "", "statements": []})
    contribs: Dict[str, dict] = defaultdict(
        lambda: {"label": "", "description": "", "paper": "", "statements": []}
    )
    problems: Dict[str, dict] = defaultdict(lambda: {"label": "", "papers": []})

    n = 0
    with open(dump_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            n += 1
            if n % 1_000_000 == 0:
                print(f"  ...{n:,} triples", file=sys.stderr)
            m = RE_SUBJ.match(line)
            if not m:
                continue
            s = _short(m.group(1))
            p = _short(m.group(2))
            o_text = m.group(3)
            o = _obj(o_text)
            o_is_uri = _is_uri(o_text)

            # predicate labels: <.../predicate/P34> rdfs:label "evaluation"
            if s.startswith("predicate/") and p == "rdfs:label":
                predicates[s] = o
                continue

            # skip type-triples on predicates themselves
            if p == "rdf:type":
                t = o
                resources[s]["types"].append(t)
                if t == "class/Paper":
                    papers[s]["label"] = resources[s]["label"]
                elif t == "class/Problem":
                    problems[s]["label"] = resources[s]["label"]
                elif t == "class/Contribution":
                    contribs[s]["label"] = resources[s]["label"]
                continue

            if p == "rdfs:label" and not s.startswith("predicate/"):
                resources[s]["label"] = o
                if s in papers:
                    papers[s]["label"] = o
                if s in problems:
                    problems[s]["label"] = o
                if s in contribs:
                    contribs[s]["label"] = o
            elif (p == "description" or p == "SCHEMAORG:description") and not s.startswith("predicate/"):
                resources[s]["description"] = o
                if s in contribs:
                    contribs[s]["description"] = o

            # paper -> contribution (P31 = "contribution")
            if p == "predicate/P31" and s in papers:
                papers[s]["contributions"].append(o)
                contribs[o]["paper"] = s

            # paper -> research problem (P32 = "has research problem"); subject may
            # be a Paper OR a Contribution that belongs to a paper.
            if p == "predicate/P32" and o_is_uri and o in problems:
                if s in papers and o not in papers[s]["problems"]:
                    papers[s]["problems"].append(o)
                    problems[o]["papers"].append(s)
                elif s in contribs:
                    pid = contribs[s]["paper"]
                    if pid and pid in papers and o not in papers[pid]["problems"]:
                        papers[pid]["problems"].append(o)
                        problems[o]["papers"].append(pid)

            # contribution statements: subject is a Contribution, predicate is a P-code
            if s in contribs and p.startswith("predicate/") and o:
                pred_label = predicates.get(p, p)
                contribs[s]["statements"].append((pred_label, o if o_is_uri else o))

            # paper-level predicate statements (year P29, field P30, etc.)
            if s in papers and p.startswith("predicate/") and o:
                pred_label = predicates.get(p, p)
                papers[s]["statements"].append((pred_label, o))
                if p == "predicate/P29":
                    mm = re.search(r"(1[89]\d{2}|20\d{2})", o)
                    if mm:
                        papers[s]["year"] = int(mm.group(1))
                elif p == "predicate/P30":
                    papers[s]["field_ref"] = o

    return {
        "predicates": predicates,
        "papers": {k: dict(v) for k, v in papers.items()},
        "contribs": {k: dict(v) for k, v in contribs.items()},
        "problems": {k: dict(v) for k, v in problems.items()},
        "resources": {k: dict(v) for k, v in resources.items() if (v["label"] or v["description"])},
        "triples": n,
    }


if __name__ == "__main__":
    dump = Path(DUMP).expanduser()
    print(f"Parsing {dump} ...", file=sys.stderr)
    idx = parse(str(dump))
    print(f"Parsed {idx['triples']:,} triples.", file=sys.stderr)
    print(f"  predicates: {len(idx['predicates']):,}", file=sys.stderr)
    print(f"  resources : {len(idx['resources']):,}", file=sys.stderr)
    print(f"  papers    : {len(idx['papers']):,}", file=sys.stderr)
    print(f"  contribs  : {len(idx['contribs']):,}", file=sys.stderr)
    print(f"  problems  : {len(idx['problems']):,}", file=sys.stderr)
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(idx, ensure_ascii=False))
    print(f"Wrote index -> {OUT}", file=sys.stderr)
