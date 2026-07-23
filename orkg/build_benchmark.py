"""build_benchmark.py — construct a TRUE temporal rediscovery benchmark from ORKG.

The Popper pipeline (schema / generate / score / corpus) is UNCHANGED. The only
independent variable in this experiment is the corpus: curated hand-built
benchmarks -> the ORKG knowledge graph. To keep the pipeline byte-for-byte
identical we emit ORKG-derived corpora in the EXACT benchmark JSON schema that
`popper.corpus.load_benchmark` already reads:

    {domain, title, is_false?, discovery_year, held_out_paper{id,citation,doi},
     ground_truth_hypothesis, ground_truth_variables{...},
     prior_literature:[{id,title,doi,year,claims[]}]}

Temporal holdout protocol (this is what makes it a rediscovery benchmark and not
just "generate from the whole graph"):

  1. Pick an ORKG research problem (P32) that has many papers spanning several years.
  2. Sort its papers by publication year.
  3. Choose a HELD-OUT "discovery" paper: a well-formed later paper whose
     contribution states a clear finding. Its contribution becomes the
     ground-truth hypothesis the compiler must reconstruct.
  4. prior_literature = ONLY papers strictly earlier than the held-out year.
     Nothing from the discovery year or later leaks in. This is the temporal wall.
  5. The compiler sees only prior knowledge and must reconstruct the leap.

Successes AND failures are both kept. A failure (low rediscovery match) is
evidence the temporal wall holds and the benchmark is not leaking future
information — it is a feature, not a bug.

Domains are assigned from the ORKG research field (P30) so we can report
per-discipline generalization (biomedicine, chemistry, materials, neuroscience,
computer science, ...).
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

INDEX = sys.argv[1] if len(sys.argv) > 1 else "build_orkg/index.json"
OUTDIR = Path(sys.argv[2] if len(sys.argv) > 2 else "benchmark_orkg")

# --- discipline mapping: ORKG research-field label substrings -> our domain buckets
DISCIPLINE_RULES = [
    ("biomedicine", ["biolog", "medic", "health", "clinical", "cancer", "gene",
                      "protein", "cell", "disease", "drug", "immun", "genom",
                      "bioinformatic", "vaccine", "brain", "neuro"]),
    ("neuroscience", ["neuro", "brain", "cognit", "eeg", "fmri"]),
    ("chemistry", ["chemi", "catalys", "molecul", "reaction", "compound",
                   "spectroscop", "polymer"]),
    ("materials_science", ["material", "nanomaterial", "alloy", "semiconductor",
                           "crystal", "graphene", "battery", "photovolta"]),
    ("computer_science", ["comput", "machine learning", "deep learning", "neural network",
                          "software", "algorithm", "data", "segmentation",
                          "classification", "nlp", "natural language", "image",
                          "requirements engineering", "network", "security"]),
    ("physics", ["physic", "quantum", "particle", "energy", "optic", "photon"]),
    ("environmental_science", ["climate", "co2", "emission", "environment",
                               "ecolog", "sustainab", "carbon"]),
]

YEAR_PRED_HINTS = ("year", "date", "publication")
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")


def _discipline(field_label: str) -> str:
    fl = (field_label or "").lower()
    for name, keys in DISCIPLINE_RULES:
        if any(k in fl for k in keys):
            return name
    return "other"


def _extract_year(statements: List) -> Optional[int]:
    for pred, obj in statements:
        pl = str(pred).lower()
        if any(h in pl for h in YEAR_PRED_HINTS):
            m = YEAR_RE.search(str(obj))
            if m:
                return int(m.group(1))
    # fall back: any 4-digit year anywhere in the statements
    for _pred, obj in statements:
        m = YEAR_RE.search(str(obj))
        if m:
            y = int(m.group(1))
            if 1850 <= y <= 2025:
                return y
    return None


def short_id(uri: str) -> str:
    """Emit a clean bare id (e.g. 'R138934') the model can cite literally.

    The ORKG URI is 'http://orkg.org/orkg/resource/R138934'; the original curated
    benchmarks used bare ids like 'barrangou2007'. To keep the compiler's
    source-citation behavior identical across the two corpora, we strip the
    namespace so hypotheses cite 'R138934' rather than 'resource/R138934' (which
    the 35B model tends to drop) — otherwise grounding would be zeroed by a pure
    formatting mismatch, not by a real grounding failure.
    """
    s = str(uri).strip()
    for pre in ("http://orkg.org/orkg/", "https://orkg.org/orkg/"):
        if s.startswith(pre):
            s = s[len(pre):]
    return s.replace("resource/", "").strip("/") or s


def _resolve(obj: str, resources: Dict) -> str:
    """Turn a resource id like 'resource/R123' into its human label if possible."""
    if isinstance(obj, str) and obj.startswith("resource/") and obj in resources:
        lab = resources[obj].get("label") or resources[obj].get("description")
        if lab:
            return lab
    return str(obj)


# ORKG predicates that carry scientific content (as opposed to bibliographic
# metadata like venue / author / data-availability). We prefer these when
# building readable claim strings.
CONTENT_PREDS = ("result", "finding", "conclusion", "method", "approach",
                 "material", "model", "metric", "evaluation", "dataset",
                 "hypothesis", "research question answer", "contribution",
                 "objective", "outcome", "measure", "property", "mechanism",
                 "effect", "factor", "topic investigated", "research  question",
                 "research question")
SKIP_PREDS = ("venue", "author", "doi", "url", "data availability", "field",
              "paradigm", "has research problem", "research problem", "same as")


def _stmt_claims(statements: List, resources: Dict) -> List[str]:
    content, other = [], []
    for pred, obj in statements:
        pl = str(pred).lower().strip()
        if any(h in pl for h in YEAR_PRED_HINTS):
            continue
        if any(sk in pl for sk in SKIP_PREDS):
            continue
        val = _resolve(obj, resources).strip()
        if not val or (val == obj and str(obj).startswith("resource/")):
            continue
        text = f"{pred.strip()}: {val}"
        if not (8 <= len(text) <= 300):
            continue
        (content if any(cp in pl for cp in CONTENT_PREDS) else other).append(text)
    return content + other


def _paper_claims(paper: dict, contribs: Dict, resources: Dict,
                  max_claims: int = 6) -> List[str]:
    """Readable claim strings from a paper's contributions (+ paper statements)."""
    claims: List[str] = []
    for cid in paper.get("contributions", []):
        c = contribs.get(cid)
        if not c:
            continue
        if c.get("description"):
            claims.append(c["description"].strip())
        claims.extend(_stmt_claims(c.get("statements", []), resources))
    # de-dup preserving order
    seen = set()
    out = []
    for c in claims:
        k = c.lower()
        if k not in seen:
            seen.add(k)
            out.append(c)
        if len(out) >= max_claims:
            break
    return out


def _paper_year(paper: dict, contribs: Dict) -> Optional[int]:
    if paper.get("year"):
        return int(paper["year"])
    stmts = []
    for cid in paper.get("contributions", []):
        c = contribs.get(cid)
        if c:
            stmts.extend(c.get("statements", []))
    return _extract_year(stmts)


def build(index: Dict, min_prior: int = 4, max_prior: int = 10,
          max_domains_per_discipline: int = 3) -> List[dict]:
    papers = index["papers"]
    contribs = index["contribs"]
    problems = index["problems"]
    resources = index.get("resources", {})

    # research field per paper: prefer paper-level P30 (field_ref), fall back to
    # the problem label and any contribution "field" statement.
    def field_of(paper: dict) -> str:
        ref = paper.get("field_ref")
        if ref:
            lab = _resolve(ref, resources)
            if lab and not str(lab).startswith("resource/"):
                return lab
        for cid in paper.get("contributions", []):
            c = contribs.get(cid, {})
            for pred, obj in c.get("statements", []):
                if "field" in str(pred).lower():
                    return _resolve(obj, resources)
        return ""

    benchmarks: List[dict] = []
    per_discipline: Dict[str, int] = defaultdict(int)

    # rank problems by number of papers (richest first)
    ranked = sorted(problems.items(),
                    key=lambda kv: len(kv[1].get("papers", [])), reverse=True)

    for pid, prob in ranked:
        paper_ids = prob.get("papers", [])
        if len(paper_ids) < min_prior + 1:
            continue
        # gather papers with a resolvable year and >=1 claim
        rows: List[Tuple[int, str, dict, List[str]]] = []
        disc_votes: Dict[str, int] = defaultdict(int)
        for pidx in paper_ids:
            p = papers.get(pidx)
            if not p:
                continue
            yr = _paper_year(p, contribs)
            claims = _paper_claims(p, contribs, resources)
            if yr is None or len(claims) < 1:
                continue
            rows.append((yr, pidx, p, claims))
            disc_votes[_discipline(field_of(p))] += 1
        if len(rows) < min_prior + 1:
            continue
        rows.sort(key=lambda r: r[0])
        discipline = max(disc_votes.items(), key=lambda kv: kv[1])[0] if disc_votes else "other"
        if discipline == "other":
            continue
        if per_discipline[discipline] >= max_domains_per_discipline:
            continue

        # held-out discovery paper = the latest paper that has the richest claims
        # among the top-third-by-year, so prior literature is genuinely earlier.
        n = len(rows)
        late = rows[max(1, (2 * n) // 3):]  # later third
        held = max(late, key=lambda r: len(r[3]))
        held_year = held[0]
        prior = [r for r in rows if r[0] < held_year]
        if len(prior) < min_prior:
            # widen: take everything strictly earlier even if few
            prior = [r for r in rows if r[0] < held_year]
        if len(prior) < min_prior:
            continue
        prior = prior[-max_prior:]  # most recent prior papers, capped

        prob_label = prob.get("label") or pid
        held_p = held[2]
        gt_claims = held[3]
        held_title = held_p.get("label", "") or ""
        # Synthesize a ground-truth statement from the held-out paper's title +
        # its most content-bearing claims, so the rediscovery axis compares
        # against the actual later finding, not just the problem name.
        gt_body = "; ".join(gt_claims[:3]) if gt_claims else ""
        ground_truth = (
            f"For the research problem '{prob_label}', the held-out later work "
            f"({held_title[:120]}) established: {gt_body}" if gt_body
            else f"{prob_label}: {held_title}")

        bench = {
            "domain": f"orkg_{discipline}_{re.sub(r'[^a-z0-9]+', '_', prob_label.lower())[:32].strip('_')}",
            "title": f"{prob_label} ({discipline})",
            "discipline": discipline,
            "orkg_problem_id": pid,
            "discovery_year": held_year,
            "is_false": False,
            "held_out_paper": {
                "id": short_id(held[1]),
                "citation": held_p.get("label", held[1]),
                "doi": "",
            },
            "ground_truth_hypothesis": ground_truth,
            "ground_truth_variables": {
                "independent_variable": "",
                "dependent_variable": "",
                "measurement": "",
                "falsification_condition": "",
            },
            "prior_literature": [
                {
                    "id": short_id(pidx),
                    "title": p.get("label", pidx),
                    "doi": "",
                    "year": yr,
                    "claims": claims,
                }
                for (yr, pidx, p, claims) in prior
            ],
        }
        benchmarks.append(bench)
        per_discipline[discipline] += 1

    return benchmarks


if __name__ == "__main__":
    idx = json.loads(Path(INDEX).read_text())
    print(f"loaded index: {idx.get('triples','?')} triples, "
          f"{len(idx['papers'])} papers, {len(idx['problems'])} problems",
          file=sys.stderr)
    benches = build(idx)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    by_disc: Dict[str, int] = defaultdict(int)
    for b in benches:
        by_disc[b["discipline"]] += 1
        (OUTDIR / f"{b['domain']}.json").write_text(
            json.dumps(b, indent=2, ensure_ascii=False))
    print(f"wrote {len(benches)} temporal-holdout benchmarks -> {OUTDIR}",
          file=sys.stderr)
    for d, n in sorted(by_disc.items()):
        print(f"  {d}: {n}", file=sys.stderr)
