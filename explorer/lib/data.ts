// lib/data.ts — load the compiled falsifiability report + per-domain hypotheses.
// Data is copied from ../../build into ./data at deploy time.

import report from '../data/report.json';

export type Evidence = {
  claim: string;
  source_id: string;
  source_title?: string;
  stance: string;
  quote?: string;
};

export type Prediction = {
  intervention: string;
  expected_effect: string;
  direction: string;
  magnitude_low: number | null;
  magnitude_high: number | null;
  unit: string;
  confidence: number;
  supporting_count: number;
  contradictory_count: number;
} | null;

export type Hypothesis = {
  id: string;
  statement: string;
  independent_variable: string;
  dependent_variable: string;
  population: string;
  measurement: string;
  expected_outcome: string;
  falsification_condition: string;
  mechanism: string;
  prediction: Prediction;
  evidence: Evidence[];
  novelty: number;
  grounding: number;
  testability: number;
  expert_agreement: number;
  composite: number;
  source_ids: string[];
  method: string;
  notes: string;
  falsifiable: boolean;
  validation_errors: string[];
};

export type MethodAgg = {
  n: number;
  n_falsifiable: number;
  falsifiable_rate: number;
  mean_novelty: number | null;
  mean_grounding: number | null;
  mean_testability: number | null;
  mean_expert_agreement: number | null;
  mean_composite: number | null;
  max_expert_agreement: number;
};

export type DomainSummary = {
  domain: string;
  title: string;
  discipline?: string;
  is_benchmark: boolean;
  is_false: boolean;
  n_sources: number;
  n_claims: number;
  ground_truth_hypothesis: string;
  held_out_paper: { id?: string; citation?: string; doi?: string };
  per_method: Record<string, MethodAgg>;
};

export type Report = {
  n: number;
  audit: boolean;
  domains: Record<string, DomainSummary>;
};

export const METHODS = ['compiler', 'llm-only', 'keyword', 'random'] as const;

export function getReport(): Report {
  return report as unknown as Report;
}

export function getDomains(): DomainSummary[] {
  return Object.values(getReport().domains);
}

// Per-domain hypotheses are bundled as a map generated at deploy time.
import hypById from '../data/hypotheses.json';
export function getHypotheses(domain: string): Hypothesis[] {
  const all = hypById as unknown as Record<string, Hypothesis[]>;
  return all[domain] || [];
}
export function allHypotheses(): Record<string, Hypothesis[]> {
  return hypById as unknown as Record<string, Hypothesis[]>;
}

// ---- ORKG-specific reports ----
import ablation from '../data/ablation.json';
import grounding from '../data/grounding.json';
import adversarial from '../data/adversarial.json';
import meta from '../data/meta.json';

export type CompAgg = {
  n: number;
  n_falsifiable: number;
  falsifiable_rate: number;
  mean_novelty: number | null;
  mean_grounding: number | null;
  mean_testability: number | null;
  mean_expert_agreement: number | null;
  mean_composite: number | null;
  max_expert_agreement: number;
};

export type AblationReport = {
  n?: number;
  audit?: boolean;
  components: string[];
  ablation_domains?: string[];
  per_domain: Record<string, Record<string, CompAgg>>;
};

export type GroundingTier = {
  n_evidence: number;
  fully_grounded: number;
  partially_grounded: number;
  unsupported: number;
  fully_grounded_rate: number;
  partially_grounded_rate: number;
  unsupported_rate: number;
  hallucinated_ids: number;
  discipline?: string;
};

export type GroundingReport = GroundingTier & {
  per_domain: Record<string, GroundingTier>;
};

export type AdversarialCase = {
  title: string;
  held_out_paper: { id?: string; citation?: string; doi?: string };
  ground_truth_hypothesis: string;
  n: number;
  mean_composite: number | null;
  mean_grounding: number | null;
  mean_testability: number | null;
  mean_expert_agreement: number | null;
  mean_novelty: number | null;
  n_falsifiable: number;
  max_expert_agreement: number;
  evidence_audit: GroundingTier;
  note: string;
};

export type DiscStat = {
  domains: number;
  mean_composite: number | null;
  mean_grounding: number | null;
  mean_rediscovery: number | null;
  mean_falsifiable_rate: number | null;
};

export type Meta = {
  n_domains: number;
  n_adversarial: number;
  disciplines: Record<string, DiscStat>;
  n_hypotheses: number;
  ablation_domains: string[];
  audit: boolean;
};

export function getAblation(): AblationReport {
  return ablation as unknown as AblationReport;
}
export function getGrounding(): GroundingReport {
  return grounding as unknown as GroundingReport;
}
export function getAdversarial(): Record<string, AdversarialCase> {
  return adversarial as unknown as Record<string, AdversarialCase>;
}
export function getMeta(): Meta {
  return meta as unknown as Meta;
}
