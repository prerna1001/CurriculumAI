"use client";

import { useState } from "react";
import { ApiError, publish, search, select } from "@/lib/api";
import {
  STYLE_LABEL,
  type Card,
  type PublishResponse,
  type SearchResponse,
  type SelectResponse,
  type TeachingStyle,
} from "@/lib/types";

const STYLE_CLASS: Record<TeachingStyle, string> = {
  theory: "bg-indigo-50 text-indigo-800 ring-indigo-200",
  case_study: "bg-amber-50 text-amber-900 ring-amber-200",
  project: "bg-emerald-50 text-emerald-800 ring-emerald-200",
};

export default function Home() {
  const [subject, setSubject] = useState("Introduction to Machine Learning");
  const [level, setLevel] = useState("undergraduate");

  const [result, setResult] = useState<SearchResponse | null>(null);
  const [previousOrder, setPreviousOrder] = useState<string[] | null>(null);
  const [chosen, setChosen] = useState<Set<string>>(new Set());

  // Kept deliberately separate from `result`: a new search must never erase
  // the outline the professor already approved.
  const [selection, setSelection] = useState<SelectResponse | null>(null);
  const [published, setPublished] = useState<PublishResponse | null>(null);

  const [busy, setBusy] = useState<"search" | "select" | "publish" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const searchCount = previousOrder ? 2 : result ? 1 : 0;

  async function run<T>(kind: "search" | "select" | "publish", fn: () => Promise<T>) {
    setBusy(kind);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function onSearch(event: React.FormEvent) {
    event.preventDefault();
    const previous = result?.cards.map((c) => c.title) ?? null;
    const next = await run("search", () => search(subject, level));
    if (!next) return;
    setPreviousOrder(previous);
    setResult(next);
    setChosen(new Set());
  }

  async function onCommit() {
    if (!result || chosen.size === 0) return;
    const next = await run("select", () => select(result.session_id, [...chosen]));
    if (!next) return;
    setSelection(next);
    setPublished(null);
  }

  async function onPublish() {
    if (!selection) return;
    const next = await run("publish", () => publish(selection.selection_id));
    if (next) setPublished(next);
  }

  function toggle(id: string) {
    setChosen((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }

  // Matched on title, not id: the backend scopes card ids to the search
  // session, so the same topic carries a different id on every search. A topic
  // that did not appear last time gets no badge rather than a misleading one.
  function rankDelta(title: string, index: number): number | null {
    if (!previousOrder) return null;
    const before = previousOrder.indexOf(title);
    return before === -1 ? null : before - index;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-10">
        <h1 className="text-2xl font-semibold tracking-tight">CurriculumAI</h1>
        <p className="mt-2 text-sm text-stone-600">
          Pick the topics you would actually teach. The agents learn your teaching
          style from those choices and rank the next set differently.
        </p>
      </header>

      <form onSubmit={onSearch} className="mb-8 grid gap-3 sm:grid-cols-[1fr_11rem_auto]">
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Subject"
          aria-label="Subject"
          className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm outline-none focus:border-stone-500"
        />
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          aria-label="Level"
          className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm outline-none focus:border-stone-500"
        >
          <option value="introductory">Introductory</option>
          <option value="undergraduate">Undergraduate</option>
          <option value="graduate">Graduate</option>
        </select>
        <button
          type="submit"
          disabled={busy !== null || !subject.trim()}
          className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {busy === "search"
            ? "Researching…"
            : searchCount === 0
              ? "Find topics"
              : "Search again"}
        </button>
      </form>

      {error && (
        <p className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      {busy === "search" && (
        <p className="mb-6 text-sm text-stone-500">
          Searching the live web and drafting candidates — this takes a moment.
        </p>
      )}

      {result && (
        <section className="mb-10">
          <div className="mb-4 flex items-baseline justify-between gap-4 border-b border-stone-200 pb-3">
            <h2 className="text-sm font-semibold">Recommended topics</h2>
            <span className="text-xs text-stone-500">
              profile v{result.profile_version}
            </span>
          </div>

          <p className="mb-5 text-sm text-stone-600">{result.preference_summary}</p>

          <ul className="space-y-3">
            {result.cards.map((card, index) => (
              <TopicCard
                key={card.id}
                card={card}
                delta={rankDelta(card.title, index)}
                checked={chosen.has(card.id)}
                onToggle={() => toggle(card.id)}
              />
            ))}
          </ul>

          <button
            onClick={onCommit}
            disabled={busy !== null || chosen.size === 0}
            className="mt-5 rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {busy === "select"
              ? "Saving…"
              : `Use these topics${chosen.size ? ` (${chosen.size})` : ""}`}
          </button>
        </section>
      )}

      {selection && (
        <section className="rounded-xl border border-stone-200 bg-white p-6">
          <div className="mb-5 rounded-lg bg-amber-50 px-4 py-3 ring-1 ring-amber-200">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
              What the agents learned
            </p>
            <p className="mt-1 text-sm text-amber-950">{selection.learned_change}</p>
            <p className="mt-1 text-xs text-amber-800">
              {selection.preference_summary} Search again to see the ranking move.
            </p>
          </div>

          <h2 className="text-lg font-semibold tracking-tight">
            {selection.outline.title}
          </h2>
          <p className="mt-1 mb-5 text-xs text-stone-500">
            Selection {selection.selection_id} · approved outline, saved and immutable
          </p>

          <ol className="space-y-5">
            {selection.outline.sessions.map((session, i) => (
              <li key={i} className="border-t border-stone-200 pt-4">
                <h3 className="text-sm font-medium">
                  <span className="mr-2 text-stone-400 tabular-nums">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {session.topic}
                </h3>
                <dl className="mt-2 space-y-2 text-sm">
                  <Field label="Activity">{session.activity}</Field>
                  <Field label="Learning objective">{session.learning_objective}</Field>
                  <Field label="Sources">
                    <ul className="space-y-0.5">
                      {session.source_references.map((ref) => (
                        <li key={ref.source_id}>
                          <a
                            href={ref.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sky-800 underline decoration-sky-300 underline-offset-2 break-all"
                          >
                            {ref.source_id}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </Field>
                </dl>
              </li>
            ))}
          </ol>

          <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-stone-200 pt-5">
            <button
              onClick={onPublish}
              disabled={busy !== null || published?.status === "published"}
              className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              {busy === "publish"
                ? "Publishing…"
                : published?.status === "published"
                  ? "Published"
                  : "Approve & publish"}
            </button>

            {published?.status === "published" && published.external_url && (
              <a
                href={published.external_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-sky-800 underline decoration-sky-300 underline-offset-2"
              >
                Open published artifact ↗
              </a>
            )}
            {published?.status === "publishing" && (
              <span className="text-sm text-stone-500">Still publishing…</span>
            )}
            {published?.status === "failed" && (
              <span className="text-sm text-red-700">Publishing failed.</span>
            )}
          </div>
        </section>
      )}
    </main>
  );
}

// Source URLs originate from the web via the research agent, so they are not
// guaranteed to parse.
function hostname(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return "source";
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[0.6875rem] font-medium uppercase tracking-wide text-stone-400">
        {label}
      </dt>
      <dd className="mt-0.5 text-stone-700">{children}</dd>
    </div>
  );
}

function TopicCard({
  card,
  delta,
  checked,
  onToggle,
}: {
  card: Card;
  delta: number | null;
  checked: boolean;
  onToggle: () => void;
}) {
  // The input is a sibling of the label, not a child: nesting it makes a click
  // on the box itself fire twice (once natively, once forwarded by the label)
  // and cancel out. The source link sits outside the label so following it
  // never toggles the selection.
  const inputId = `topic-${card.id}`;

  return (
    <li>
      <div
        className={`flex gap-3 rounded-xl border bg-white p-4 transition ${
          checked ? "border-stone-900 ring-1 ring-stone-900" : "border-stone-200 hover:border-stone-300"
        }`}
      >
        <input
          id={inputId}
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          className="mt-1 size-4 shrink-0 accent-stone-900"
        />
        <div className="min-w-0">
          <label htmlFor={inputId} className="block cursor-pointer">
            <span className="mb-1.5 flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full px-2 py-0.5 text-[0.6875rem] font-medium ring-1 ${STYLE_CLASS[card.teaching_style]}`}
              >
                {STYLE_LABEL[card.teaching_style]}
              </span>
              {delta !== null && delta !== 0 && (
                <span
                  className={`rounded-full px-2 py-0.5 text-[0.6875rem] font-medium tabular-nums ${
                    delta > 0 ? "bg-emerald-100 text-emerald-800" : "bg-stone-100 text-stone-500"
                  }`}
                  title="Change in rank since the previous search"
                >
                  {delta > 0 ? `↑ ${delta}` : `↓ ${Math.abs(delta)}`}
                </span>
              )}
            </span>
            <span className="block text-sm font-medium leading-snug">{card.title}</span>
            <span className="mt-1 block text-sm text-stone-600">{card.description}</span>
            <span className="mt-2 block text-xs text-stone-500">{card.why_suggested}</span>
          </label>
          <a
            href={card.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1.5 inline-block text-xs text-sky-800 underline decoration-sky-300 underline-offset-2 break-all"
          >
            {hostname(card.source_url)} ↗
          </a>
        </div>
      </div>
    </li>
  );
}
