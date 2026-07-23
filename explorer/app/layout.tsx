import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Popper-ORKG — Does compile-time knowledge organization generalize?',
  description:
    'The identical Popper falsifiable-hypothesis compiler, run on the Open Research Knowledge Graph (6.3M triples, 65k papers) instead of curated benchmarks. Temporal rediscovery, four-way controls, a component ablation, an expanded adversarial set, and a full grounding audit — all compiled locally on a 35B model.',
};

const nav = [
  ['/', 'Overview'],
  ['/domains', 'Domains'],
  ['/rediscovery', 'Rediscovery'],
  ['/ablation', 'Ablation'],
  ['/controls', 'Controls'],
  ['/grounding', 'Grounding'],
  ['/adversarial', 'Adversarial'],
  ['/hypotheses', 'Hypotheses'],
  ['/method', 'Method'],
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif', background: '#0a0e1a', color: '#e6e9f0' }}>
        <header style={{ borderBottom: '1px solid #1e2740', padding: '14px 22px', display: 'flex', gap: 18, alignItems: 'center', flexWrap: 'wrap' }}>
          <Link href="/" style={{ color: '#7dd3fc', fontWeight: 800, textDecoration: 'none', fontSize: 17, letterSpacing: 0.3 }}>
            Popper-ORKG<span style={{ color: '#5b6680', fontWeight: 400 }}> · does it generalize?</span>
          </Link>
          <nav style={{ display: 'flex', gap: 14, marginLeft: 'auto', flexWrap: 'wrap' }}>
            {nav.map(([href, label]) => (
              <Link key={href} href={href} style={{ color: '#aab2c8', textDecoration: 'none', fontSize: 14 }}>{label}</Link>
            ))}
          </nav>
        </header>
        <main style={{ maxWidth: 1080, margin: '0 auto', padding: '26px 22px 80px' }}>{children}</main>
        <footer style={{ borderTop: '1px solid #1e2740', padding: '18px 22px', color: '#5b6680', fontSize: 12, textAlign: 'center' }}>
          local-first · identical Popper pipeline · only the corpus changed (curated → ORKG) · compiled on a 35B model · no cloud APIs
        </footer>
      </body>
    </html>
  );
}
