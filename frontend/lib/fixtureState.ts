/**
 * In-memory fixture backend for lane A.
 *
 * Exists so the frontend can be built and the learning loop demonstrated before
 * B's FastAPI backend is live. It implements the same contracts and the same
 * deterministic ranking rule, so the UI written against it does not change when
 * NEXT_PUBLIC_API_BASE is pointed at the real backend.
 *
 * Fixture mode is for development only. The accepted demo uses real services.
 */

import fs from "node:fs";
import path from "node:path";
import type {
  Card,
  Outline,
  SearchResponse,
  SelectResponse,
  TeachingStyle,
} from "./types";

const CONTRACTS = path.join(process.cwd(), "..", "contracts");

type Counts = Record<TeachingStyle, number>;

interface FixtureState {
  counts: Counts;
  version: number;
  sessions: Map<string, { cards: Card[]; baselineOrder: string[] }>;
  selections: Map<string, { outline: Outline; sessionId: string }>;
  seq: number;
}

// Survive hot reload in dev, otherwise the profile resets on every edit.
const g = globalThis as unknown as { __curriculumAIFixture?: FixtureState };

function state(): FixtureState {
  if (!g.__curriculumAIFixture) {
    g.__curriculumAIFixture = {
      counts: { theory: 1, case_study: 1, project: 1 },
      version: 0,
      sessions: new Map(),
      selections: new Map(),
      seq: 0,
    };
  }
  return g.__curriculumAIFixture;
}

function readContract<T>(name: string): T {
  return JSON.parse(fs.readFileSync(path.join(CONTRACTS, name), "utf-8")) as T;
}

function baselineCards(): Card[] {
  return readContract<SearchResponse>("search.response.json").cards;
}

export function resetFixture(): void {
  g.__curriculumAIFixture = undefined;
}

// --- the learning rule (mirrors backend/learning/, deterministic) ----------

function weights(counts: Counts): Record<TeachingStyle, number> {
  const total = counts.theory + counts.case_study + counts.project;
  return {
    theory: counts.theory / total,
    case_study: counts.case_study / total,
    project: counts.project / total,
  };
}

function summarise(counts: Counts): string {
  const w = weights(counts);
  const ordered = (Object.keys(w) as TeachingStyle[]).sort((a, b) => w[b] - w[a]);
  const spread = w[ordered[0]] - w[ordered[2]];
  if (spread < 0.01) {
    return "No teaching-style preference recorded yet. Showing a balanced set.";
  }
  const parts = ordered.map((s) => `${s} (${w[s].toFixed(2)})`);
  return `Prefers ${parts[0]}, then ${parts[1]} and ${parts[2]}.`;
}

/** Order by descending style weight; ties broken by original candidate order. */
function rank(cards: Card[], counts: Counts): Card[] {
  const w = weights(counts);
  return cards
    .map((card, index) => ({ card, index }))
    .sort((a, b) => {
      const delta = w[b.card.teaching_style] - w[a.card.teaching_style];
      return delta !== 0 ? delta : a.index - b.index;
    })
    .map((entry) => entry.card);
}

// --- endpoints -------------------------------------------------------------

export function fixtureSearch(subject: string, level: string): SearchResponse {
  const s = state();
  s.seq += 1;
  const sessionId = `sess_${s.seq}`;
  const base = baselineCards();
  const ordered = rank(base, s.counts);

  s.sessions.set(sessionId, {
    cards: ordered,
    baselineOrder: base.map((c) => c.id),
  });

  return {
    session_id: sessionId,
    profile_version: s.version,
    preference_summary: summarise(s.counts),
    // The subject is echoed into the first card so it is visible that the
    // request reached the backend; the real backend researches it properly.
    cards: ordered.map((c, i) =>
      i === 0 ? { ...c, why_suggested: `${c.why_suggested} (${subject}, ${level})` } : c,
    ),
  };
}

export function fixtureSelect(sessionId: string, cardIds: string[]): SelectResponse {
  const s = state();
  const session = s.sessions.get(sessionId);
  if (!session) {
    throw new FixtureError(422, "invalid_input", "Unknown session_id.", false);
  }

  const unique = Array.from(new Set(cardIds));
  if (unique.length === 0) {
    throw new FixtureError(422, "invalid_input", "Select at least one topic.", false);
  }

  const selected = unique
    .map((id) => session.cards.find((c) => c.id === id))
    .filter((c): c is Card => Boolean(c));
  if (selected.length !== unique.length) {
    throw new FixtureError(422, "invalid_input", "A card does not belong to this session.", false);
  }

  const before = weights(s.counts);
  for (const card of selected) s.counts[card.teaching_style] += 1;
  s.version += 1;
  const after = weights(s.counts);

  s.seq += 1;
  const selectionId = `sel_${s.seq}`;
  const outline = buildOutline(selected);
  s.selections.set(selectionId, { outline, sessionId });

  return {
    selection_id: selectionId,
    profile_version: s.version,
    learned_change: describeChange(before, after),
    preference_summary: summarise(s.counts),
    outline,
  };
}

export function fixturePublish(selectionId: string) {
  const s = state();
  const saved = s.selections.get(selectionId);
  if (!saved) {
    throw new FixtureError(422, "invalid_input", "Unknown selection_id.", false);
  }
  return {
    selection_id: selectionId,
    status: "published" as const,
    external_id: `fixture_${selectionId}`,
    external_url: `https://example-destination.test/d/fixture_${selectionId}`,
  };
}

// --- helpers ---------------------------------------------------------------

function describeChange(
  before: Record<TeachingStyle, number>,
  after: Record<TeachingStyle, number>,
): string {
  const styles = Object.keys(after) as TeachingStyle[];
  const moved = styles
    .map((s) => ({ s, delta: after[s] - before[s] }))
    .sort((a, b) => b.delta - a.delta)[0];

  // Be honest: a balanced selection genuinely changes nothing.
  if (moved.delta < 0.005) {
    return "Balanced selection — style weights are unchanged, so ranking will not move.";
  }
  return `${moved.s} weight rose from ${before[moved.s].toFixed(2)} to ${after[moved.s].toFixed(2)}.`;
}

function buildOutline(selected: Card[]): Outline {
  // The crafted fixture outline, when the selection matches the contract example.
  const ids = selected.map((c) => c.id).sort().join(",");
  if (ids === "card_3,card_4") {
    return readContract<SelectResponse>("select.response.json").outline;
  }
  return {
    title: `Module draft from ${selected.length} selected ${selected.length === 1 ? "topic" : "topics"}`,
    sessions: selected.map((card) => ({
      topic: card.title,
      activity: card.description,
      learning_objective: `Apply the ideas in "${card.title}" to an unfamiliar example and defend the result.`,
      source_references: [{ source_id: `src_${card.id}`, url: card.source_url }],
    })),
  };
}

export class FixtureError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly retryable: boolean,
  ) {
    super(message);
  }
}
