import { getAdversarial } from '../../lib/data';
import { card, fmt, ScoreBar } from '../../lib/ui';

export default function Adversarial() {
  const cases = Object.entries(getAdversarial());

  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>Adversarial negative controls — attractive nonsense</h1>
      <p style={{ color: '#aab2c8', maxWidth: 820, lineHeight: 1.65 }}>
        A trustworthy discovery system must <i>not</i> rank historically-plausible-but-false theories
        highly. These seven are canonical dead ends whose narratives fit their prior evidence well:
        cold fusion, phlogiston, N-rays, the luminiferous aether, caloric, Lamarckian inheritance, and
        miasma theory. We want their <b>rediscovery match to be low</b>. A medium score should be
        explainable by grounded evidence and honest uncertainty — not by mere narrative plausibility.
      </p>

      {cases.length === 0 && (
        <div style={{ ...card, borderColor: '#fbbf2455' }}>
          <span style={{ color: '#fbbf24' }}>Adversarial results pending — the run is still in progress.</span>
        </div>
      )}

      {cases.map(([dom, c]) => {
        const match = c.max_expert_agreement;
        const matchColor = match <= 0.34 ? '#34d399' : match <= 0.66 ? '#fbbf24' : '#f87171';
        const a = c.evidence_audit || ({} as typeof c.evidence_audit);
        return (
          <div key={dom} style={{ ...card, marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#e6e9f0', maxWidth: 620 }}>{c.title}</div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 26, fontWeight: 800, color: matchColor }}>{fmt(match)}</div>
                <div style={{ fontSize: 11, color: '#5b6680' }}>rediscovery match (lower = better)</div>
              </div>
            </div>
            <p style={{ color: '#8892a8', fontSize: 13, lineHeight: 1.55, marginTop: 8 }}>{c.note}</p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 14, marginTop: 10 }}>
              <div>
                <ScoreBar label="composite" value={c.mean_composite} />
                <ScoreBar label="grounding" value={c.mean_grounding} />
                <ScoreBar label="testability" value={c.mean_testability} />
                <ScoreBar label="novelty" value={c.mean_novelty} />
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#5b6680', marginBottom: 6 }}>Evidence provenance ({a.n_evidence ?? 0} items)</div>
                <div style={{ fontSize: 13, color: '#34d399' }}>fully grounded: {fmt(a.fully_grounded_rate)}</div>
                <div style={{ fontSize: 13, color: '#fbbf24' }}>partial: {fmt(a.partially_grounded_rate)}</div>
                <div style={{ fontSize: 13, color: '#f87171' }}>unsupported: {fmt(a.unsupported_rate)}</div>
                <div style={{ fontSize: 12, color: '#aab2c8', marginTop: 4 }}>hallucinated ids: {a.hallucinated_ids ?? 0}</div>
              </div>
            </div>
            <div style={{ fontSize: 12, color: '#5b6680', marginTop: 8 }}>
              why the score: a false theory can still be <i>falsifiable</i> ({c.n_falsifiable}/{c.n} were)
              and even partly grounded in real prior work — but the reconstruction should NOT match the
              (false) ground-truth claim, and the composite is capped by whatever it cannot ground.
            </div>
          </div>
        );
      })}
    </div>
  );
}
