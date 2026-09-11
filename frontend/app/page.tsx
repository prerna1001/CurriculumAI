"use client";

import { useState } from "react";
import ImprovementPanel from "./ImprovementPanel";
import { ApiError, publish, search, select } from "@/lib/api";
import {
  STYLE_LABEL,
  type Card,
  type PublishResponse,
  type SearchResponse,
  type SelectResponse,
  type TeachingStyle,
} from "@/lib/types";

const STYLE_COLOR: Record<TeachingStyle, string> = {
  theory: "var(--theory)",
  case_study: "var(--accent)",
  project: "var(--project)",
};

// The weight-bar gutter is too narrow for "Case study" to sit on one line.
const SHORT_LABEL: Record<TeachingStyle, string> = {
  theory: "Theory",
  case_study: "Case",
  project: "Project",
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

  const [busy, setBusy] = useState<"search" | "select" | "publish" | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const searchCount = previousOrder ? 2 : result ? 1 : 0;

  async function run<T>(
    kind: "search" | "select" | "publish",
    fn: () => Promise<T>,
  ) {
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
    const next = await run("select", () =>
      select(result.session_id, [...chosen]),
    );
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
    <div className="mx-auto grid max-w-[764px] grid-cols-1 gap-12 px-6 pb-24 pt-16 xl:max-w-[1136px] xl:grid-cols-[764px_300px]">
      <main>
        <header className="flex flex-col gap-3.5">
          <div className="flex items-center gap-2.5">
            <div
              className="h-px w-[22px]"
              style={{ background: "var(--accent)" }}
            />
            <span className="label" style={{ color: "var(--accent)" }}>
              Curriculum design · learning agent
            </span>
          </div>
          <h1 className="serif m-0 text-[46px] font-medium leading-none tracking-[-0.02em]">
            CurriculumAI
          </h1>
          <p
            className="serif m-0 max-w-[33em] text-[18px] italic leading-[1.5]"
            style={{ color: "var(--ink-2)", textWrap: "pretty" }}
          >
            Pick the topics you would actually teach. The agents learn your
            teaching style from those choices, and go looking for different
            material next time.
          </p>
        </header>

        <div className="my-8 h-px" style={{ background: "var(--rule)" }} />

        <form
          onSubmit={onSearch}
          className="grid gap-3 sm:grid-cols-[1fr_190px_150px]"
        >
          <Field label="Subject">
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="What are you teaching?"
              aria-label="Subject"
              className="w-full rounded-[3px] border px-3.5 py-3 text-[14.5px]"
              style={{ background: "var(--card)", borderColor: "var(--field)" }}
            />
          </Field>
          <Field label="Level">
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              aria-label="Level"
              className="w-full appearance-none rounded-[3px] border px-3.5 py-3 text-[14.5px]"
              style={{ background: "var(--card)", borderColor: "var(--field)" }}
            >
              <option value="introductory">Introductory</option>
              <option value="undergraduate">Undergraduate</option>
              <option value="graduate">Graduate</option>
            </select>
          </Field>
          <Field>
            <button
              type="submit"
              disabled={busy !== null || !subject.trim()}
              className="label w-full rounded-[3px] px-4 py-3.5 disabled:opacity-35"
              style={{ background: "var(--ink)", color: "var(--paper)" }}
            >
              {busy === "search"
                ? "Researching…"
                : searchCount === 0
                  ? "Find topics"
                  : "Search again"}
            </button>
          </Field>
        </form>

        {error && (
          <p
            className="mt-6 rounded-[3px] border px-4 py-3 text-sm"
            style={{
              background: "#fdf2f0",
              borderColor: "#e8cdc6",
              color: "#8a3323",
            }}
          >
            {error}
          </p>
        )}

        {busy === "search" && (
          <p className="mt-6 text-[13px]" style={{ color: "var(--ink-4)" }}>
            Searching the live web and drafting candidates — this takes a
            moment.
          </p>
        )}

        {result && (
          <section className="mt-12">
            <div
              className="flex items-baseline justify-between gap-4 border-b pb-3"
              style={{ borderColor: "var(--ink)" }}
            >
              <span className="label" style={{ fontSize: "11px" }}>
                Recommended topics
              </span>
              <span
                className="mono text-[11px]"
                style={{ color: "var(--ink-4)" }}
              >
                profile v{result.profile_version}
              </span>
            </div>

            <div className="mt-[18px] mb-6 flex flex-wrap items-start justify-between gap-8">
              <p
                className="serif m-0 max-w-[26em] text-[16px] leading-[1.5]"
                style={{ color: "var(--ink-2)" }}
              >
                {result.preference_summary}
              </p>
              <WeightBars summary={result.preference_summary} />
            </div>

            <ul className="flex list-none flex-col gap-0.5 p-0">
              {result.cards.map((card, index) => (
                <TopicCard
                  key={card.id}
                  card={card}
                  index={index}
                  delta={rankDelta(card.title, index)}
                  checked={chosen.has(card.id)}
                  onToggle={() => toggle(card.id)}
                />
              ))}
            </ul>

            <div className="mt-6 flex flex-wrap items-center gap-4">
              <button
                onClick={onCommit}
                disabled={busy !== null || chosen.size === 0}
                className="label rounded-[3px] px-5 py-3 disabled:opacity-35"
                style={{ background: "var(--ink)", color: "var(--paper)" }}
              >
                {busy === "select"
                  ? "Saving…"
                  : `Use these topics${chosen.size ? ` · ${chosen.size}` : ""}`}
              </button>
              <span className="text-[12.5px]" style={{ color: "var(--ink-4)" }}>
                Your picks train the next search.
              </span>
            </div>
          </section>
        )}

        {selection && (
          <>
            <div
              className="mt-13 rounded-[3px] border px-6 py-6"
              style={{
                background: "var(--accent-bg)",
                borderColor: "var(--accent-border)",
                borderLeft: "3px solid var(--accent)",
              }}
            >
              <div className="mb-3 flex items-center gap-2.5">
                <TrendIcon />
                <span
                  className="label"
                  style={{ fontSize: "10px", color: "var(--accent)" }}
                >
                  What the agents learned
                </span>
              </div>
              <p
                className="serif m-0 text-[21px] leading-[1.4] tracking-[-0.005em]"
                style={{ color: "var(--accent-ink)", textWrap: "pretty" }}
              >
                {selection.learned_change}
              </p>
              <p
                className="mt-2.5 text-[13px] leading-[1.6]"
                style={{ color: "var(--accent-soft)" }}
              >
                {selection.preference_summary} The next search reweights the
                ranking <em>and</em> rewrites the query sent to the web.
              </p>
            </div>

            <section
              className="mt-4 rounded-[3px] border px-9 py-8"
              style={{ background: "var(--card)", borderColor: "var(--field)" }}
            >
              <div
                className="flex items-baseline justify-between gap-5 border-b pb-4"
                style={{ borderColor: "var(--ink)" }}
              >
                <span
                  className="label"
                  style={{ fontSize: "10px", color: "var(--ink-4)" }}
                >
                  Approved outline
                </span>
                <span
                  className="mono text-[10px]"
                  style={{ color: "var(--ink-5)" }}
                >
                  {selection.selection_id.slice(0, 12)} · immutable
                </span>
              </div>

              <h2
                className="serif mt-5 max-w-[20em] text-[28px] font-medium leading-[1.22] tracking-[-0.015em]"
                style={{ textWrap: "pretty" }}
              >
                {selection.outline.title}
              </h2>

              <ol className="mt-7 flex list-none flex-col gap-6 p-0">
                {selection.outline.sessions.map((session, i) => (
                  <li key={i} className="flex flex-col gap-6">
                    {i > 0 && (
                      <div
                        className="h-px"
                        style={{ background: "var(--rule-soft)" }}
                      />
                    )}
                    <div className="flex gap-5">
                      <span
                        className="mono shrink-0 pt-1 text-[12px]"
                        style={{ color: "var(--accent)" }}
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div className="flex min-w-0 flex-col gap-3.5">
                        <h3 className="serif m-0 text-[18px] font-semibold leading-[1.3]">
                          {session.topic}
                        </h3>
                        <Detail label="Activity">{session.activity}</Detail>
                        <Detail label="Learning objective">
                          {session.learning_objective}
                        </Detail>
                        <div className="flex flex-col gap-1.5">
                          <span
                            className="label"
                            style={{ fontSize: "9px", color: "var(--ink-5)" }}
                          >
                            {session.source_references.length === 1
                              ? "Source"
                              : "Sources"}
                          </span>
                          <div className="flex flex-col gap-1">
                            {session.source_references.map((ref) => (
                              <a
                                key={ref.source_id}
                                href={ref.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="self-start break-all text-[12.5px]"
                              >
                                {sourceLabel(ref.url)} ↗
                              </a>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ol>

              <div
                className="mt-8 flex flex-wrap items-center gap-4 border-t pt-6"
                style={{ borderColor: "var(--rule-soft)" }}
              >
                <button
                  onClick={onPublish}
                  disabled={busy !== null || published?.status === "published"}
                  className="label flex items-center gap-2.5 rounded-[3px] px-5 py-3 disabled:opacity-45"
                  style={{ background: "var(--accent)", color: "var(--card)" }}
                >
                  <SendIcon />
                  {busy === "publish"
                    ? "Publishing…"
                    : published?.status === "published"
                      ? "Published"
                      : "Approve & publish"}
                </button>

                {published?.status === "published" && published.external_url ? (
                  <a
                    href={published.external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[12.5px]"
                  >
                    Open published artifact ↗
                  </a>
                ) : published?.status === "publishing" ? (
                  <span
                    className="text-[12.5px]"
                    style={{ color: "var(--ink-4)" }}
                  >
                    Still publishing…
                  </span>
                ) : published?.status === "failed" ? (
                  <span className="text-[12.5px]" style={{ color: "#8a3323" }}>
                    Publishing failed.
                  </span>
                ) : (
                  <span
                    className="text-[12.5px]"
                    style={{ color: "var(--ink-4)" }}
                  >
                    Rendered in a sandbox, delivered to your inbox.
                  </span>
                )}
              </div>
            </section>
          </>
        )}
      </main>

      <div className="xl:sticky xl:top-16 xl:self-start">
        <ImprovementPanel refreshKey={selection?.profile_version ?? 0} />
      </div>
    </div>
  );
}

/* ---------- pieces ---------- */

function Field({
  label,
  children,
}: {
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-[7px]">
      {/* Keeps the button baseline aligned with the labelled inputs beside it. */}
      <span
        className="label"
        style={{ color: "var(--ink-4)" }}
        aria-hidden={!label}
      >
        {label ?? " "}
      </span>
      {children}
    </div>
  );
}

function Detail({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span
        className="label"
        style={{ fontSize: "9px", color: "var(--ink-5)" }}
      >
        {label}
      </span>
      <p
        className="serif m-0 text-[15.5px] leading-[1.6]"
        style={{ color: "#3d372f", textWrap: "pretty" }}
      >
        {children}
      </p>
    </div>
  );
}

function TopicCard({
  card,
  index,
  delta,
  checked,
  onToggle,
}: {
  card: Card;
  index: number;
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
    <li
      className="flex gap-[18px] rounded-[3px] border px-[22px] py-5 transition-colors"
      style={{
        background: "var(--card)",
        borderColor: checked ? "#d8cdb9" : "var(--rule-soft)",
        borderLeft: `3px solid ${checked ? "var(--accent)" : "var(--rule-soft)"}`,
      }}
    >
      <div className="flex w-[22px] shrink-0 flex-col items-center gap-2.5">
        <span className="mono text-[11px]" style={{ color: "var(--ink-5)" }}>
          {String(index + 1).padStart(2, "0")}
        </span>
        <input
          id={inputId}
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          className="size-4 cursor-pointer rounded-[2px]"
          style={{ accentColor: "var(--ink)" }}
        />
      </div>

      <div className="flex min-w-0 flex-col gap-[7px]">
        <label
          htmlFor={inputId}
          className="flex cursor-pointer flex-col gap-[7px]"
        >
          <span className="flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1.5">
              <span
                className="size-[5px] rounded-full"
                style={{ background: STYLE_COLOR[card.teaching_style] }}
              />
              <span
                className="label"
                style={{ color: STYLE_COLOR[card.teaching_style] }}
              >
                {STYLE_LABEL[card.teaching_style]}
              </span>
            </span>
            {delta !== null && delta !== 0 && <DeltaTag delta={delta} />}
          </span>
          <span className="serif block text-[20px] font-medium leading-[1.25] tracking-[-0.005em]">
            {card.title}
          </span>
          <span
            className="block text-[14px] leading-[1.55]"
            style={{ color: "var(--ink-2)", textWrap: "pretty" }}
          >
            {card.description}
          </span>
          <span
            className="serif mt-0.5 block text-[14px] italic leading-[1.5]"
            style={{ color: "#857b70" }}
          >
            {card.why_suggested}
          </span>
        </label>
        <a
          href={card.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 self-start break-all text-[11px] tracking-[0.04em]"
        >
          {hostname(card.source_url)} ↗
        </a>
      </div>
    </li>
  );
}

function DeltaTag({ delta }: { delta: number }) {
  const up = delta > 0;
  return (
    <span
      className="mono flex items-center gap-[3px] text-[10px]"
      style={{ color: up ? "var(--project)" : "#a0958a" }}
      title="Change in rank since the previous search"
    >
      <svg
        width="9"
        height="9"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points={up ? "18 15 12 9 6 15" : "6 9 12 15 18 9"} />
      </svg>
      {Math.abs(delta)}
    </span>
  );
}

/**
 * Renders the weights the summary already states, as bars.
 * The API returns the summary as prose, so this parses it and simply renders
 * nothing when the wording does not match — never a wrong bar.
 */
function WeightBars({ summary }: { summary: string }) {
  const weights = [...summary.matchAll(/([a-z_]+)\s*\(([01]?\.\d+)\)/gi)].map(
    (m) => ({
      style: m[1] as TeachingStyle,
      value: Number(m[2]),
    }),
  );

  if (weights.length !== 3 || weights.some((w) => !STYLE_LABEL[w.style]))
    return null;

  return (
    <div className="flex w-[188px] shrink-0 flex-col gap-[7px]">
      {weights.map((w) => (
        <div key={w.style} className="flex items-center gap-2.5">
          <span
            className="label w-14 shrink-0 text-right"
            style={{
              fontSize: "9px",
              letterSpacing: "0.08em",
              color: "var(--ink-4)",
            }}
          >
            {SHORT_LABEL[w.style]}
          </span>
          <div
            className="h-[5px] flex-grow overflow-hidden rounded-full"
            style={{ background: "#e8e0d3" }}
          >
            <div
              className="h-full transition-[width] duration-500"
              style={{
                width: `${Math.round(w.value * 100)}%`,
                background: w.value >= 0.4 ? "var(--accent)" : "#b9ad9a",
              }}
            />
          </div>
          <span
            className="mono w-6 text-[9.5px]"
            style={{ color: "var(--ink-2)" }}
          >
            {w.value.toFixed(2).replace("0.", ".")}
          </span>
        </div>
      ))}
    </div>
  );
}

function TrendIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--accent)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 17l6-6 4 4 8-8" />
      <polyline points="21 3 21 9 15 9" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M22 2L11 13" />
      <path d="M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  );
}

// Source URLs originate from the web via the research agent, so they are not
// guaranteed to parse.
function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "source";
  }
}

// Outline citations show host + a short path, so a reader can tell two
// references from the same site apart.
function sourceLabel(url: string): string {
  try {
    const { hostname: host, pathname } = new URL(url);
    const short = pathname.length > 28 ? `${pathname.slice(0, 27)}…` : pathname;
    return `${host.replace(/^www\./, "")}${short === "/" ? "" : short}`;
  } catch {
    return "source";
  }
}
