import Link from 'next/link';
import { getDomains } from '../../lib/data';
import { card, fmt } from '../../lib/ui';

export default function Domains() {
  const domains = getDomains();
  const byDisc: Record<string, typeof domains> = {};
  for (const d of domains) (byDisc[d.discipline || '?'] ||= []).push(d);
  const disciplines = Object.keys(byDisc).sort();

  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>Domains — temporal-holdout benchmarks across disciplines</h1>
      <p style={{ color: '#aab2c8', maxWidth: 820, lineHeight: 1.65 }}>
        Each domain is a real ORKG research problem. We hold out a later &quot;discovery&quot; paper and give
        the compiler <b>only strictly-earlier prior literature</b> (the temporal wall). Grouped by
        discipline so you can see whether grounding, falsifiability, and composite stay stable across
        fields or whether some expose weaknesses in the schema.
      </p>

      {domains.length === 0 && (
        <div style={{ ...card, borderColor: '#fbbf2455' }}>
          <span style={{ color: '#fbbf24' }}>Domain results pending — the run is still in progress.</span>
        </div>
      )}

      {disciplines.map((disc) => (
        <div key={disc} style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, textTransform: 'capitalize', color: '#7dd3fc' }}>{disc.replace(/_/g, ' ')}</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
            {byDisc[disc].map((d) => {
              const cm = d.per_method.compiler;
              return (
                <Link key={d.domain} href="/hypotheses" style={{ textDecoration: 'none' }}>
                  <div style={{ ...card }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#e6e9f0', marginBottom: 4 }}>{d.title}</div>
                    <div style={{ fontSize: 12, color: '#5b6680', marginBottom: 8 }}>
                      {d.n_sources} prior papers · {d.n_claims} claims · held out {d.held_out_paper?.id}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                      <span style={{ color: '#aab2c8' }}>composite</span>
                      <span style={{ color: '#7dd3fc', fontWeight: 700 }}>{fmt(cm?.mean_composite)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                      <span style={{ color: '#aab2c8' }}>grounding</span>
                      <span style={{ color: '#34d399' }}>{fmt(cm?.mean_grounding)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                      <span style={{ color: '#aab2c8' }}>falsifiable</span>
                      <span style={{ color: '#aab2c8' }}>{fmt(cm?.falsifiable_rate)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                      <span style={{ color: '#aab2c8' }}>rediscovery</span>
                      <span style={{ color: '#fbbf24' }}>{fmt(cm?.max_expert_agreement)}</span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
