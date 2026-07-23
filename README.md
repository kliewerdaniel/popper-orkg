# Popper-ORKG — Does compile-time knowledge organization generalize?

**The experiment in one sentence:** take the *identical* Popper falsifiable-hypothesis
compiler — same schema, same scoring rubric, same grounding audit, same four-way
control structure — and change **only the corpus**, from a handful of hand-curated
benchmark literatures to the **Open Research Knowledge Graph (ORKG)**: 6.3M triples,
65,689 papers, 8,420 research problems. Then ask whether the central claim still holds.

> **Central hypothesis under test:** *Compile-time organization of scientific
> knowledge produces higher-quality, grounded, falsifiable hypotheses than
> unstructured generation.*

This repo is built so that claim can **fail**, and reports the number either way.

---

## Why this experiment

The original [Popper](https://github.com/kliewerdaniel/popper) run showed the compiler
beat its controls on five hand-built benchmark corpora (CRISPR, mRNA, checkpoint
blockade, cold fusion, phlogiston). A skeptic's obvious objection: *those corpora were
curated by the same person who built the compiler.* Maybe the result is an artifact of
clean, hand-picked prior literature.

So we hold the entire methodology fixed and swap in a large, heterogeneous, **externally
curated** knowledge graph we did not build. The only independent variable is the corpus.

## What is unchanged (the whole point)

The `popper/` package is **byte-for-byte identical** to the original run
(`md5` verified):

- `popper/schema.py` — the falsifiable hypothesis schema (IV/DV/measurement/
  falsification-condition/mechanism/quantitative-prediction/evidence). Missing a field
  is a *compile error*.
- `popper/generate.py` — the four methods: `compiler`, `llm-only`, `keyword`, `random`.
- `popper/score.py` — grounding (with LLM audit) × novelty × testability → geometric-mean
  composite; rediscovery match as a separate axis.
- `popper/corpus.py`, `popper/inference.py` — corpus abstraction + stdlib local-model client.

If any file in `popper/` differed from the original, the experiment would be
uninterpretable. It doesn't.

## What is new (the ORKG layer + the extra studies the brief asked for)

Everything ORKG-specific lives in `orkg/` and *wraps* the unchanged pipeline:

| Module | Role |
|---|---|
| `orkg/orkg_ingest.py` | Stream-parse the 855 MB `rdf-export-orkg.nt` dump once into a compact JSON index (papers, contributions, problems, predicates, resources, **publication year P29**, **research field P30**). |
| `orkg/build_benchmark.py` | Construct a **true temporal rediscovery benchmark**: pick a research problem, hold out a later "discovery" paper, keep **only strictly-earlier prior literature** (the temporal wall), emit corpora in the *exact* benchmark JSON schema the pipeline already reads. |
| `orkg/ablation.py` | Systematically remove one compiler component at a time (see below), composing the unchanged building blocks differently — never editing `popper/`. |
| `orkg/grounding_audit.py` | Classify every evidence item into `fully_grounded` / `partially_grounded` / `unsupported`, and count hallucinated (out-of-corpus) source ids. |
| `adversarial/` | Seven historically-plausible-but-false theories (cold fusion, phlogiston, N-rays, luminiferous aether, caloric, Lamarckism, miasma). |

### The temporal holdout protocol (why this isn't "generate from the whole graph")

1. Pick an ORKG research problem (P32) with many papers spanning several years.
2. Sort its papers by publication year.
3. Hold out a later, content-rich paper — its contribution becomes the ground-truth
   hypothesis the compiler must reconstruct.
4. `prior_literature` = **only** papers strictly earlier than the held-out year. Nothing
   from the discovery year or later leaks in.
5. The compiler sees only prior knowledge and must reconstruct the leap.

**Failures are kept and reported.** A low rediscovery match is evidence the temporal wall
holds and the benchmark is not leaking future information — a feature, not a bug.

### The ablation study (is the architecture load-bearing?)

Beating weak baselines isn't enough; we must show the compiler's *architecture* carries
the result. Each ablation keeps the other five components intact:

- `full` — the real compiler (ablation baseline).
- `no_graph_reasoning` — claims flattened into an unlabeled bag; no cross-source traversal.
- `no_grounding_verif` — the LLM grounding audit is switched off (presence, not support).
- `no_gap_detection` — the "find an unstated connection" objective is removed.
- `no_falsifiability` — the falsifiable-schema requirement is dropped.
- `no_lit_synthesis` — the corpus is truncated to a single source.

We measure the degradation in composite / grounding / falsifiable-rate / rediscovery from
each removal.

## Running it

```bash
# 0. one-time: parse the ORKG dump (download rdf-export-orkg.nt from orkg.org/data)
env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 orkg/orkg_ingest.py \
    ~/Downloads/rdf-export-orkg.nt build_orkg/index.json

# 1. build the temporal-holdout benchmark corpora
env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 orkg/build_benchmark.py \
    build_orkg/index.json benchmark_orkg

# 2. smoke-test the non-LLM paths (fast, no model needed)
env -u PYTHONPATH -u VIRTUAL_ENV /usr/bin/python3 smoke_test.py

# 3. the full experiment (needs a local OpenAI-compatible model on :8080)
env -u PYTHONPATH -u VIRTUAL_ENV KC_MAX_TOKENS=12000 KC_TIMEOUT=600 \
    /usr/bin/python3 run_experiment.py --n 3
```

Local model runtime: an OpenAI-compatible server on `http://localhost:8080/v1`
(this run used `deepreinforce-ai/Ornith-1.0-35B-Q4_K_M` via llama.cpp). No cloud APIs,
no keys — `popper/inference.py` is stdlib-only. Tunables: `KC_MAX_TOKENS`, `KC_TIMEOUT`,
`KC_PORT`, `KC_MODEL`.

## Outputs

```
build/<domain>/hypotheses.json     all methods, all scores, full provenance
build/<domain>/summary.json        per-method aggregates
build/<domain>/ablations.json      per-component ablation hypotheses
build/report.json                  cross-domain four-way control roll-up
build/ablation_report.json         ablation table + degradation per component
build/grounding_audit.json         provenance tiers + hallucinated-id counts
build/adversarial_report.json      per-false-case score + evidence rationale
```

## Success criteria (from the brief)

The experiment succeeds if: the compiler significantly outperforms all three controls on
ORKG; ablations produce measurable degradation; hypotheses stay traceable to ORKG
evidence; performance is consistent across disciplines; and the evaluation surfaces both
strengths and *legitimate failure modes* rather than optimizing for perfect scores.

See the [live explorer](https://popper-orkg.vercel.app) and the accompanying blog post for
the numbers and the written conclusion.

## Lineage

Third iteration of the local-first research-compiler program:
**Scientific Discovery Compiler** (generate) → **Scientific Question Compiler** (scale) →
**Popper** (falsifiable) → **Popper-ORKG** (does it generalize?).
