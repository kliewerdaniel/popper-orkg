// lib/ui.tsx — shared presentational helpers.
import React from 'react';

export const card: React.CSSProperties = {
  background: '#111a2e', border: '1px solid #1e2740', borderRadius: 12, padding: 16,
};

export function ScoreBar({ label, value }: { label: string; value: number | null }) {
  const v = value == null || value < 0 ? null : value;
  const pct = v == null ? 0 : Math.round(v * 100);
  const color = v == null ? '#5b6680' : v >= 0.66 ? '#34d399' : v >= 0.33 ? '#fbbf24' : '#f87171';
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#aab2c8' }}>
        <span>{label}</span>
        <span style={{ color }}>{v == null ? 'n/a' : v.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: '#1e2740', borderRadius: 4, overflow: 'hidden', marginTop: 3 }}>
        <div style={{ width: pct + '%', height: '100%', background: color }} />
      </div>
    </div>
  );
}

export function Pill({ text, color }: { text: string; color: string }) {
  return (
    <span style={{ fontSize: 11, color, border: `1px solid ${color}55`, background: `${color}18`, padding: '2px 8px', borderRadius: 999, textTransform: 'uppercase', letterSpacing: 0.5 }}>
      {text}
    </span>
  );
}

export const METHOD_COLOR: Record<string, string> = {
  compiler: '#7dd3fc',
  'llm-only': '#a78bfa',
  keyword: '#fbbf24',
  random: '#f87171',
};

export function fmt(v: number | null): string {
  return v == null || v < 0 ? '—' : v.toFixed(2);
}
