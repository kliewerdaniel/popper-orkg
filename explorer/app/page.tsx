import Link from 'next/link';
import { getReport, getDomains, getMeta, METHODS } from '../lib/data';
import { card, fmt, METHOD_COLOR, Pill } from '../lib/ui';

export default function Overview() {
  const report = getReport();
  const domains = getDomains();
  const meta = getMeta();
  const hasData = domains.length > 0;

  const methodComposite: Record<string, number[]> = {};
  for (const d of domains) {
    for (const m of METHODS) {
      const agg = d.per_method[m];
      if (agg && agg.mean_composite != null) (methodComposite[m] ||= []).push(agg.mean_composite);
    }
  }
  const meanOf = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
  const disciplines = Object.entries(meta.disciplines || {}).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div>
      <h1 style={{ fontSize: 30, marginTop: 0, marginBottom: 6 }}>
        Does compile-time knowledge organization <span style={{ color: '#7dd3fc' }}>generalize</span>?
      </h1>
      <p style={{ color: '#aab2c8', maxWidth: 800, lineHeight: 1.65, fontSize: 15 }}>
        Popper showed a knowledge-graph compiler beats its controls on five <i>hand-curated</i>
        benchmark literatures. The obvious objection: those corpora were built by the same person who
        built the compiler. So we hold the <b>entire methodology fixed</b> — same schema, same scoring
        rubric, same grounding audit, same four-way control structure — and change <b>only the
        corpus</b>: from curated benchmarks to the <b>Open Research Knowledge Graph</b> (6.3M triples,
        65,689 papers, 8,420 research problems). The only independent variable is the corpus.
      </p>

      {!hasData && (
        <div style={{ ...card, borderColor: '#fbbf2455', background: '#1a1607' }}>
          <b style={{ color: '#fbbf24' }}>Run in progress.</b>
          <span style={{ color: '#aab2c8' }}> The 35B compilation is still populating <code>build/</code>.
            Re-export and redeploy once it finishes.</span>
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', margin: '20px 0 8px' }}>
        {METHODS.map((m) => (
          <div key={m} style={{ ...card, minWidth: 150, flex: 1 }}>
            <div style={{ marginBottom: 8 }}><Pill text={m} color={METHOD_COLOR[m]} /></div>
            <div style={{ fontSize: 26, fontWeight: 800, color: METHOD_COLOR[m] }}>
              {hasData ? meanOf(methodComposite[m] || []).toFixed(2) : '—'}
            </div>
            <div style={{ fontSize: 11, color: '#5b6680', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              mean composite (ORKG)
            </div>
          </div>
        ))}
      </div>
      <p style={{ color: '#5b6680', fontSize: 13, maxWidth: 800 }}>
        The claim under test: <b style={{ color: '#aab2c8' }}>structured knowledge compilation produces
        higher-quality, grounded, falsifiable hypotheses than unstructured generation</b> — and that it
        holds on a large, heterogeneous corpus the author did not curate. If the compiler bar is not
        clearly above the three controls here, the claim fails to generalize, and that is the result.
      </p>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', margin: '18px 0' }}>
        {[
          ['domains', meta.n_domains, 'ORKG domains'],
          ['disciplines', disciplines.length, 'scientific disciplines'],
          ['adversarial', meta.n_adversarial, 'adversarial false theories'],
          ['hypotheses', meta.n_hypotheses, 'compiled hypotheses'],
        ].map(([k, v, label]) => (
          <div key={k as string} style={{ ...card, minWidth: 130, flex: 1 }}>
            <div style={{ fontSize: 26, fontWeight: 800, color: '#e6e9f0' }}>{v as number}</div>
            <div style={{ fontSize: 11, color: '#5b6680' }}>{label as string}</div>
          </div>
        ))}
      </div>

      {disciplines.length > 0 && (
        <>
          <h2 style={{ fontSize: 20, marginTop: 30 }}>Per-discipline generalization</h2>
          <p style={{ color: '#aab2c8', maxWidth: 800, lineHeight: 1.6 }}>
            Does the compiler hold across fields, or do some disciplines expose weaknesses in the schema?
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {disciplines.map(([disc, s]) => (
              <Link key={disc} href="/domains" style={{ textDecoration: 'none' }}>
                <div style={{ ...card }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: '#e6e9f0', textTransform: 'capitalize' }}>
                    {disc.replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontSize: 12, color: '#5b6680', marginBottom: 8 }}>{s.domains} domain(s)</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span style={{ color: '#aab2c8' }}>composite</span>
                    <span style={{ color: '#7dd3fc', fontWeight: 700 }}>{fmt(s.mean_composite)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span style={{ color: '#aab2c8' }}>grounding</span>
                    <span style={{ color: '#34d399' }}>{fmt(s.mean_grounding)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span style={{ color: '#aab2c8' }}>rediscovery</span>
                    <span style={{ color: '#fbbf24' }}>{fmt(s.mean_rediscovery)}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}

      <p style={{ color: '#5b6680', fontSize: 12, marginTop: 30 }}>
        {report.n} hypotheses per method per domain · audit {report.audit ? 'on' : 'off'} · compiled locally on a 35B model.
      </p>
    </div>
  );
}
