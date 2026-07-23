import { allHypotheses, getDomains } from '../../lib/data';
import { card, fmt, METHOD_COLOR, Pill, ScoreBar } from '../../lib/ui';
import type { Hypothesis } from '../../lib/data';

function HypCard({ h }: { h: Hypothesis }) {
  const p = h.prediction;
  return (
    <div style={{ ...card, marginBottom: 14 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' }}>
        <Pill text={h.method} color={METHOD_COLOR[h.method] || '#aab2c8'} />
        {h.falsifiable
          ? <Pill text="falsifiable" color="#34d399" />
          : <Pill text="not falsifiable" color="#f87171" />}
        <span style={{ marginLeft: 'auto', fontSize: 20, fontWeight: 800, color: '#7dd3fc' }}>{fmt(h.composite)}</span>
      </div>
      <div style={{ fontSize: 15, color: '#e6e9f0', lineHeight: 1.5 }}>{h.statement}</div>

      {(h.independent_variable || h.dependent_variable) && (
        <div style={{ fontSize: 13, color: '#aab2c8', marginTop: 8, lineHeight: 1.6 }}>
          {h.independent_variable && <><b>IV:</b> {h.independent_variable}<br /></>}
          {h.dependent_variable && <><b>DV:</b> {h.dependent_variable}<br /></>}
          {h.measurement && <><b>Measure:</b> {h.measurement}<br /></>}
          {h.falsification_condition && <><b>Refuted if:</b> {h.falsification_condition}<br /></>}
          {h.mechanism && <><b>Mechanism:</b> {h.mechanism}</>}
        </div>
      )}

      {p && (p.magnitude_low != null || p.magnitude_high != null) && (
        <div style={{ background: '#0d1424', border: '1px solid #1e2740', borderRadius: 8, padding: 10, marginTop: 10, fontSize: 13 }}>
          <b style={{ color: '#a78bfa' }}>Quantitative prediction:</b> {p.intervention} → {p.direction}{' '}
          {p.magnitude_low ?? ''}{p.magnitude_high != null ? `–${p.magnitude_high}` : ''} {p.unit} in {h.dependent_variable || 'the outcome'} · confidence {fmt(p.confidence)}
          {' · '}support {p.supporting_count} / contra {p.contradictory_count}
        </div>
      )}

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 12 }}>
        <div style={{ minWidth: 150, flex: 1 }}>
          <ScoreBar label="novelty" value={h.novelty} />
          <ScoreBar label="grounding" value={h.grounding} />
        </div>
        <div style={{ minWidth: 150, flex: 1 }}>
          <ScoreBar label="testability" value={h.testability} />
          {h.expert_agreement >= 0 && <ScoreBar label="rediscovery match" value={h.expert_agreement} />}
        </div>
      </div>

      {h.evidence.length > 0 && (
        <details style={{ marginTop: 10 }}>
          <summary style={{ cursor: 'pointer', color: '#7dd3fc', fontSize: 13 }}>
            Provenance · {h.evidence.length} evidence links
          </summary>
          <ul style={{ paddingLeft: 18, marginTop: 6 }}>
            {h.evidence.map((e, i) => (
              <li key={i} style={{ fontSize: 13, color: '#aab2c8', marginBottom: 5, lineHeight: 1.45 }}>
                <span style={{ color: e.stance === 'contradictory' ? '#f87171' : e.stance === 'contextual' ? '#fbbf24' : '#34d399' }}>[{e.stance}]</span>{' '}
                {e.claim} <span style={{ color: '#5b6680' }}>— {e.source_id}{e.source_title ? ` (${e.source_title})` : ''}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {!h.falsifiable && h.validation_errors.length > 0 && (
        <div style={{ fontSize: 12, color: '#f87171', marginTop: 8 }}>
          compile errors: {h.validation_errors.join(', ')}
        </div>
      )}
    </div>
  );
}

export default function Hypotheses() {
  const byDomain = allHypotheses();
  const domains = getDomains();
  return (
    <div>
      <h1 style={{ fontSize: 26, marginTop: 0 }}>All hypotheses</h1>
      <p style={{ color: '#aab2c8', maxWidth: 780, lineHeight: 1.6 }}>
        Every compiled artifact, with its full falsifiability record: variables, mechanism,
        quantitative prediction, per-claim provenance, and the four scores. Sorted by composite within
        each domain. Controls are included so you can see the structural difference directly.
      </p>
      {domains.map((d) => {
        const hyps = (byDomain[d.domain] || []).slice().sort((a, b) => b.composite - a.composite);
        if (!hyps.length) return null;
        return (
          <section key={d.domain} style={{ marginTop: 26 }}>
            <h2 style={{ fontSize: 19 }}>{d.title} {d.is_false && <span style={{ color: '#f87171', fontSize: 13 }}>(adversarial dead end)</span>}</h2>
            {hyps.map((h) => <HypCard key={h.id} h={h} />)}
          </section>
        );
      })}
    </div>
  );
}
