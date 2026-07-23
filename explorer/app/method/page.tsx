import { card } from '../../lib/ui';

export default function Method() {
  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>Method</h1>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.65 }}>
        Popper treats a hypothesis as a <b>compiled artifact</b>. A traditional compiler turns source
        code into an executable that must pass tests. Popper turns literature into a hypothesis that
        must pass validation.
      </p>
      <div style={{ ...card, fontFamily: 'ui-monospace, monospace', fontSize: 14, color: '#7dd3fc', margin: '14px 0' }}>
        Literature → Knowledge Compiler → Hypothesis → Validation
      </div>

      <h2 style={{ fontSize: 19 }}>The falsifiable hypothesis schema</h2>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.6 }}>
        A hypothesis is admitted only if it is structurally falsifiable. Missing an independent
        variable, a falsification condition, a quantitative prediction, or a source id is not a
        stylistic lapse — it is a <b>compile error</b>. Required fields:
      </p>
      <ul style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.7 }}>
        <li><b>Independent / dependent variable</b> — what you change, what you measure</li>
        <li><b>Population / system</b> and <b>measurement</b></li>
        <li><b>Expected outcome</b> and an explicit <b>falsification condition</b></li>
        <li><b>Mechanism</b> — the causal chain linking IV to DV</li>
        <li><b>Quantitative prediction</b> — direction + numeric magnitude window + unit + confidence</li>
        <li><b>Evidence</b> — every claim tagged with a real <code>source_id</code></li>
      </ul>

      <h2 style={{ fontSize: 19 }}>The four scores</h2>
      <ul style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.7 }}>
        <li><b>Grounding</b> — fraction of evidence with a verifiable source id, discounted by an LLM audit that checks the source actually supports the claim (catches articulate autocomplete that cites a real id for an unsupported claim).</li>
        <li><b>Testability</b> — objective structural falsifiability; how many required fields are present and non-trivial. Computed without the model.</li>
        <li><b>Novelty</b> — distance from existing corpus claims, capped low if an LLM check finds the connection is already directly stated. 1.0 = no known direct connection.</li>
        <li><b>Expert agreement (rediscovery only)</b> — semantic match to the removed ground-truth discovery.</li>
      </ul>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.6 }}>
        <b>Composite</b> is the geometric mean of the applicable scores. A zero in any dimension tanks
        the composite — by design. A beautifully written but ungrounded hypothesis must not score well.
      </p>

      <h2 style={{ fontSize: 19 }}>The experiment: only the corpus changed</h2>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.6 }}>
        This iteration holds the <b>entire Popper pipeline fixed</b> (the <code>popper/</code> package is
        byte-for-byte identical, md5-verified) and changes only the input corpus — from five curated
        benchmark literatures to the <b>Open Research Knowledge Graph</b>: 6.3M triples, 65,689 papers,
        8,420 research problems. The single independent variable is the corpus.
        <br /><br />
        <b>Temporal rediscovery:</b> for each ORKG research problem we sort papers by year, hold out a
        later &quot;discovery&quot; paper, and give the compiler <i>only strictly-earlier prior literature</i>
        (the temporal wall). Successes and failures are both reported; a failure is evidence the wall
        holds and no future information is leaking.
        <br /><br />
        <b>Four-way controls:</b> compiler vs. llm-only (no corpus) vs. keyword co-occurrence vs. random
        traversal — on the same input. <b>Component ablation:</b> remove one compiler component at a time
        (graph reasoning, grounding verification, gap detection, falsifiability eval, literature
        synthesis) and measure the degradation, to prove the architecture is load-bearing.
        <br /><br />
        <b>Adversarial (attractive nonsense):</b> seven historical dead ends — cold fusion, phlogiston,
        N-rays, luminiferous aether, caloric, Lamarckism, miasma. A trustworthy system must <i>not</i>
        reconstruct these as grounded discoveries. <b>Grounding audit:</b> every evidence item is tiered
        fully / partially / unsupported, with hallucinated out-of-corpus ids counted.
      </p>

      <h2 style={{ fontSize: 19 }}>Local-first</h2>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.6 }}>
        Every generation, audit, and score is produced by a 35B model running on the author&apos;s own
        hardware via an OpenAI-compatible endpoint — no cloud APIs, no keys. The whole point is a
        scientific instrument you can own, inspect, and rerun.
      </p>
    </div>
  );
}
