import { getAblation } from '../../lib/data';
import { card, fmt } from '../../lib/ui';

const LABELS: Record<string, string> = {
  full: 'Full compiler',
  no_graph_reasoning: 'No graph reasoning',
  no_grounding_verif: 'No grounding verification',
  no_gap_detection: 'No gap detection',
  no_falsifiability: 'No falsifiability eval',
  no_lit_synthesis: 'No literature synthesis',
};

function deltaColor(d: number | null) {
  if (d == null) return '#5b6680';
  if (d <= -0.15) return '#f87171';   // big degradation = component is load-bearing
  if (d <= -0.03) return '#fbbf24';
  return '#34d399';
}

export default function Ablation() {
  const ab = getAblation();
  const domains = Object.keys(ab.per_domain || {});
  const comps = ab.components || [];

  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>Component ablation — is the architecture load-bearing?</h1>
      <p style={{ color: '#aab2c8', maxWidth: 820, lineHeight: 1.65 }}>
        Beating weak baselines is not enough; we must show the compiler&apos;s <i>architecture</i> carries
        the result. Each row removes exactly one component and keeps the other five intact, then scores on
        the identical rubric. A large drop in composite from a removal means that component is
        <b> load-bearing</b>. If removing a component changes nothing, it was decoration.
      </p>

      {domains.length === 0 && (
        <div style={{ ...card, borderColor: '#fbbf2455' }}>
          <span style={{ color: '#fbbf24' }}>Ablation results pending — the run is still in progress.</span>
        </div>
      )}

      {domains.map((dom) => {
        const per = ab.per_domain[dom];
        const fullComp = per.full?.mean_composite ?? null;
        return (
          <div key={dom} style={{ ...card, marginBottom: 18 }}>
            <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, color: '#e6e9f0' }}>{dom}</div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13 }}>
                <thead>
                  <tr style={{ color: '#5b6680', textAlign: 'left' }}>
                    <th style={{ padding: '6px 10px' }}>Configuration</th>
                    <th style={{ padding: '6px 10px' }}>Composite</th>
                    <th style={{ padding: '6px 10px' }}>Δ vs full</th>
                    <th style={{ padding: '6px 10px' }}>Grounding</th>
                    <th style={{ padding: '6px 10px' }}>Falsifiable</th>
                    <th style={{ padding: '6px 10px' }}>Rediscovery</th>
                  </tr>
                </thead>
                <tbody>
                  {comps.map((c) => {
                    const a = per[c];
                    if (!a) return null;
                    const comp = a.mean_composite;
                    const delta = comp != null && fullComp != null ? comp - fullComp : null;
                    const isFull = c === 'full';
                    return (
                      <tr key={c} style={{ borderTop: '1px solid #1e2740', background: isFull ? '#0f1830' : 'transparent' }}>
                        <td style={{ padding: '6px 10px', fontWeight: isFull ? 700 : 400, color: isFull ? '#7dd3fc' : '#e6e9f0' }}>
                          {LABELS[c] || c}
                        </td>
                        <td style={{ padding: '6px 10px', fontWeight: 700 }}>{fmt(comp)}</td>
                        <td style={{ padding: '6px 10px', color: isFull ? '#5b6680' : deltaColor(delta), fontWeight: 700 }}>
                          {isFull ? 'baseline' : delta == null ? '—' : (delta >= 0 ? '+' : '') + delta.toFixed(3)}
                        </td>
                        <td style={{ padding: '6px 10px', color: '#aab2c8' }}>{fmt(a.mean_grounding)}</td>
                        <td style={{ padding: '6px 10px', color: '#aab2c8' }}>{fmt(a.falsifiable_rate)}</td>
                        <td style={{ padding: '6px 10px', color: '#aab2c8' }}>{fmt(a.max_expert_agreement)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
      <p style={{ color: '#5b6680', fontSize: 12 }}>
        Ablations run on one representative domain per discipline. Red Δ = large degradation = that
        component is genuinely load-bearing.
      </p>
    </div>
  );
}
