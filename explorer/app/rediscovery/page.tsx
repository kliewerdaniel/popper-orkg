import { getDomains, getHypotheses, METHODS } from '../../lib/data';
import { card, fmt, METHOD_COLOR, Pill, ScoreBar } from '../../lib/ui';

export default function Rediscovery() {
  const domains = getDomains().filter((d) => d.is_benchmark && !d.is_false);

  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>Rediscovery benchmark</h1>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.65 }}>
        For each historical discovery we <b>removed the discovery paper</b> and gave every method only
        the prior literature that existed <i>before</i> it. The test: does the compiler reconstruct the
        known scientific leap — and does it beat the controls at doing so? Each score below is the
        semantic match between a generated hypothesis and the actual ground-truth discovery (0–1).
      </p>

      {domains.map((d) => {
        const hyps = getHypotheses(d.domain);
        return (
          <div key={d.domain} style={{ ...card, marginBottom: 22 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: 19, margin: '2px 0' }}>{d.title}</h2>
              <span style={{ fontSize: 12, color: '#5b6680' }}>
                held-out paper: {d.held_out_paper?.id} · {d.n_sources} prior sources · {d.n_claims} claims
              </span>
            </div>
            <div style={{ background: '#0d1424', border: '1px solid #1e2740', borderRadius: 8, padding: 12, margin: '10px 0' }}>
              <div style={{ fontSize: 11, color: '#5b6680', textTransform: 'uppercase', letterSpacing: 0.5 }}>Ground truth (removed)</div>
              <div style={{ color: '#e6e9f0', lineHeight: 1.55, marginTop: 4 }}>{d.ground_truth_hypothesis}</div>
            </div>

            <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
              {METHODS.map((m) => {
                const agg = d.per_method[m];
                return (
                  <div key={m} style={{ flex: 1, minWidth: 190 }}>
                    <div style={{ marginBottom: 6 }}><Pill text={m} color={METHOD_COLOR[m]} /></div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: METHOD_COLOR[m] }}>
                      {fmt(agg?.max_expert_agreement ?? -1)}
                    </div>
                    <div style={{ fontSize: 11, color: '#5b6680', marginBottom: 6 }}>best rediscovery match</div>
                    <ScoreBar label="composite" value={agg?.mean_composite ?? null} />
                    <ScoreBar label="grounding" value={agg?.mean_grounding ?? null} />
                  </div>
                );
              })}
            </div>

            {/* best compiler hypothesis */}
            {(() => {
              const comp = hyps.filter((h) => h.method === 'compiler')
                .sort((a, b) => b.expert_agreement - a.expert_agreement)[0];
              if (!comp) return null;
              return (
                <details style={{ marginTop: 12 }}>
                  <summary style={{ cursor: 'pointer', color: '#7dd3fc', fontSize: 14 }}>
                    Best compiler reconstruction (match {fmt(comp.expert_agreement)})
                  </summary>
                  <div style={{ color: '#e6e9f0', lineHeight: 1.55, marginTop: 8 }}>{comp.statement}</div>
                  <div style={{ fontSize: 13, color: '#aab2c8', marginTop: 6 }}>
                    <b>IV:</b> {comp.independent_variable} · <b>DV:</b> {comp.dependent_variable}
                  </div>
                  <div style={{ fontSize: 13, color: '#aab2c8', marginTop: 4 }}><b>Mechanism:</b> {comp.mechanism}</div>
                  <div style={{ fontSize: 12, color: '#5b6680', marginTop: 6 }}>
                    grounded on: {comp.source_ids.join(', ')}
                  </div>
                </details>
              );
            })()}
          </div>
        );
      })}
    </div>
  );
}
