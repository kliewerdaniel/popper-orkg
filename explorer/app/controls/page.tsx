import { getDomains, METHODS } from '../../lib/data';
import { card, fmt, METHOD_COLOR, Pill } from '../../lib/ui';

export default function Controls() {
  const domains = getDomains();

  // aggregate each metric per method across all domains
  const metrics = ['mean_composite', 'mean_novelty', 'mean_grounding', 'mean_testability'] as const;
  const labels: Record<string, string> = {
    mean_composite: 'Composite', mean_novelty: 'Novelty',
    mean_grounding: 'Grounding', mean_testability: 'Testability',
  };
  const table: Record<string, Record<string, number[]>> = {};
  for (const m of METHODS) {
    table[m] = {};
    for (const mt of metrics) table[m][mt] = [];
  }
  for (const d of domains) {
    for (const m of METHODS) {
      const agg = d.per_method[m];
      if (!agg) continue;
      for (const mt of metrics) {
        const v = agg[mt];
        if (v != null) table[m][mt].push(v as number);
      }
    }
  }
  const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>Negative controls</h1>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.65 }}>
        The most important part of the experiment. An LLM is excellent at producing plausible
        narratives, so the compiler could &quot;succeed&quot; for the wrong reason. We run three
        controls on the <i>same</i> corpus so the only variable is the reasoning:
      </p>
      <ul style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.7 }}>
        <li><b style={{ color: METHOD_COLOR['random'] }}>random</b> — connect two random claims. Does the compiler beat noise?</li>
        <li><b style={{ color: METHOD_COLOR['keyword'] }}>keyword</b> — most frequent co-occurring concepts, templated. Does semantic reasoning beat co-occurrence statistics?</li>
        <li><b style={{ color: METHOD_COLOR['llm-only'] }}>llm-only</b> — same model, same ask, but <i>no corpus</i>. Does the knowledge graph actually help?</li>
        <li><b style={{ color: METHOD_COLOR['compiler'] }}>compiler</b> — the real method: grounded, structured compilation.</li>
      </ul>

      <div style={{ ...card, overflowX: 'auto', marginTop: 18 }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 14 }}>
          <thead>
            <tr>
              <th style={th}>method</th>
              {metrics.map((mt) => <th key={mt} style={th}>{labels[mt]}</th>)}
              <th style={th}>falsifiable rate</th>
            </tr>
          </thead>
          <tbody>
            {METHODS.map((m) => {
              const frates = domains.map((d) => d.per_method[m]?.falsifiable_rate).filter((x) => x != null) as number[];
              return (
                <tr key={m}>
                  <td style={td}><Pill text={m} color={METHOD_COLOR[m]} /></td>
                  {metrics.map((mt) => {
                    const v = mean(table[m][mt]);
                    return <td key={mt} style={{ ...td, color: METHOD_COLOR[m], fontWeight: 700 }}>{fmt(v)}</td>;
                  })}
                  <td style={td}>{fmt(mean(frates))}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p style={{ color: '#5b6680', fontSize: 13, marginTop: 14, maxWidth: 780 }}>
        Read this as the falsification test of the whole project. If the <b style={{ color: '#7dd3fc' }}>compiler</b> row
        is not clearly higher than the control rows on composite and grounding — and if the controls&apos;
        falsifiable-rate is not far lower — then structured compilation is not adding what we claim, and
        we report that honestly.
      </p>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid #1e2740', color: '#5b6680', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5 };
const td: React.CSSProperties = { padding: '10px 12px', borderBottom: '1px solid #141c30' };
