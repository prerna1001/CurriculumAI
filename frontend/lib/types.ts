// Mirrors contracts/. If these disagree with contracts/, contracts/ wins.

export type TeachingStyle = "theory" | "case_study" | "project";

export interface Card {
  id: string;
  title: string;
  description: string;
  teaching_style: TeachingStyle;
  source_url: string;
  why_suggested: string;
}

export interface SearchResponse {
  session_id: string;
  profile_version: number;
  preference_summary: string;
  cards: Card[];
}

export interface SourceReference {
  source_id: string;
  url: string;
}

export interface OutlineSession {
  topic: string;
  activity: string;
  learning_objective: string;
  source_references: SourceReference[];
}

export interface Outline {
  title: string;
  sessions: OutlineSession[];
}

export interface SelectResponse {
  selection_id: string;
  profile_version: number;
  learned_change: string;
  preference_summary: string;
  outline: Outline;
}

export type PublishStatus = "publishing" | "published" | "failed";

export interface PublishResponse {
  selection_id: string;
  status: PublishStatus;
  external_id: string | null;
  external_url: string | null;
}

export interface ErrorBody {
  error: { code: string; message: string; retryable: boolean };
}

export interface EvalPoint {
  n: number;
  version: number;
  weights: Record<TeachingStyle, number>;
  top2_share: number | null;
  mean_rank: number | null;
  changed: boolean | null;
  at: string | null;
}

export interface EvalsResponse {
  selections: number;
  profile_version: number;
  current_weights: Record<TeachingStyle, number>;
  preference_summary: string;
  points: EvalPoint[];
  top2_share_first: number | null;
  top2_share_latest: number | null;
  top2_share_delta: number | null;
  unchanged_selections: number;
  replay_consistent: boolean;
}

export const STYLE_LABEL: Record<TeachingStyle, string> = {
  theory: "Theory",
  case_study: "Case study",
  project: "Project",
};
