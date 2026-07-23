import { getGrounding } from '../../lib/data';
import { card, fmt } from '../../lib/ui';

function Bar({ full, partial, unsupported }: { full: number; partial: number; unsupported: number }) {
  const total = full + partial + unsupported || 1;
  const seg = (v: number, color: string) => (
    <div style={{ width: `${(v / total) * 100}%`, background: color, height: '100%' }} />
  );
  return (
    <div style={{ display: 'flex', height: 14, borderRadius: 6, overflow: 'hidden', background: '#1e2740' }}>
      {seg(full, '#34d399')}
      {seg(partial, '#fbbf24')}
      {seg(unsupported, '#f87171')}
    </div>
  );
}

export default function Grounding() {
  const g = getGrounding();
  const perDomain = Object.entries(g.per_domain || {});

  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>Grounding audit — is every claim traceable to ORKG?</h1>
      <p style={{ color: '#aab2c8', maxWidth: 820, lineHeight: 1.65 }}>
        Every generated hypothesis must carry complete provenance. We classify <b>each evidence item</b>
        into three tiers: <span style={{ color: '#34d399' }}>fully grounded</span> (a real in-corpus
        source id the audit confirms supports the claim), <span style={{ color: '#fbbf24' }}>partially
        grounded</span> (real id but the audit was inconclusive), and <span style={{ color: '#f87171' }}>
        unsupported</span> (missing/placeholder id, a hallucinated out-of-corpus id, or the audit judged
        the source does not support the claim).
      </p>

      {g.n_evidence ? (
        <div style={{ ...card, marginBottom: 20 }}>
          <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>Overall ({g.n_evidence} evidence items)</div>
          <Bar full={g.fully_grounded} partial={g.partially_grounded} unsupported={g.unsupported} />
          <div style={{ display: 'flex', gap: 20, marginTop: 10, fontSize: 13, flexWrap: 'wrap' }}>
            <span style={{ color: '#34d399' }}>fully {fmt(g.fully_grounded_rate)}</span>
            <span style={{ color: '#fbbf24' }}>partial {fmt(g.partially_grounded_rate)}</span>
            <span style={{ color: '#f87171' }}>unsupported {fmt(g.unsupported_rate)}</span>
            <span style={{ color: '#aab2c8' }}>hallucinated ids: {g.hallucinated_ids}</span>
          </div>
        </div>
      ) : (
        <div style={{ ...card, borderColor: '#fbbf2455' }}>
          <span style={{ color: '#fbbf24' }}>Grounding audit pending — the run is still in progress.</span>
        </div>
      )}

      {perDomain.map(([dom, t]) => (
        <div key={dom} style={{ ...card, marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, flexWrap: 'wrap', gap: 6 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{dom}</span>
            <span style={{ fontSize: 12, color: '#5b6680' }}>
              {t.discipline} · {t.n_evidence} items · halluc {t.hallucinated_ids}
            </span>
          </div>
          <Bar full={t.fully_grounded} partial={t.partially_grounded} unsupported={t.unsupported} />
        </div>
      ))}
    </div>
  );
}
