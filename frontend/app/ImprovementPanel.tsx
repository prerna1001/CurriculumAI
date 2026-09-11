"use client";

import { useEffect, useRef, useState } from "react";
import * as Plot from "@observablehq/plot";
import { evals } from "@/lib/api";
import {
  STYLE_LABEL,
  type EvalsResponse,
  type TeachingStyle,
} from "@/lib/types";

/**
 * Chart palette. Deliberately NOT the ink colours used for the style dots in
 * the main column: those sit at L 0.36–0.41 with chroma under 0.08, which the
 * dataviz palette validator fails as too dark and too grey to read as chart
 * fills. These are the same hues lifted into the passing band — validated for
 * lightness, chroma floor, CVD separation (worst adjacent pair ΔE 9.0 deutan),
 * normal-vision separation (ΔE 16.2) and contrast against the card surface.
 */
const STYLE_CHART: Record<TeachingStyle, string> = {
  case_study: "#a4690f",
  theory: "#4a63c8",
  project: "#2f8a63",
};

const ORDER: TeachingStyle[] = ["case_study", "theory", "project"];
const SURFACE = "#fffdfa";
const ACCENT = "#a4690f";
const UP = "#2f8a63";

export default function ImprovementPanel({
  refreshKey,
  onData,
}: {
  refreshKey: number;
  /** Lets the page collapse the side rail when there is nothing to show. */
  onData?: (hasData: boolean) => void;
}) {
  const [data, setData] = useState<EvalsResponse | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    evals().then((next) => {
      if (cancelled) return;
      setData(next);
      onData?.(next !== null && next.selections > 0);
    });
    return () => {
      cancelled = true;
    };
    // onData is a setState wrapper; including it would refetch on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  useEffect(() => {
    const host = chartRef.current;
    const scored = data?.points.filter((p) => p.top2_share !== null) ?? [];
    if (!host || scored.length < 2) return;

    const rows = scored.map((p) => ({
      selection: p.n,
      share: p.top2_share as number,
    }));

    const chart = Plot.plot({
      // Panel is 300px with 20px padding each side — anything wider than 260
      // gives the whole rail a horizontal scrollbar.
      width: 256,
      height: 96,
      marginTop: 8,
      marginRight: 8,
      marginBottom: 20,
      marginLeft: 28,
      style: {
        background: "transparent",
        fontFamily: "var(--font-plex-sans), system-ui, sans-serif",
        fontSize: "9px",
        color: "#8b8177",
      },
      x: {
        label: null,
        ticks: rows.map((r) => r.selection),
        tickFormat: (v: number) => String(v),
        tickSize: 0,
        tickPadding: 6,
      },
      y: {
        label: null,
        domain: [0, 1],
        ticks: [0, 0.5, 1],
        tickFormat: (v: number) => `${Math.round(v * 100)}%`,
        tickSize: 0,
        tickPadding: 4,
      },
      marks: [
        Plot.gridY({ stroke: "#e4ddd1", strokeOpacity: 1, strokeWidth: 1 }),
        Plot.ruleY([0], { stroke: "#d8cdb9", strokeWidth: 1 }),
        // Single series, so no legend — the heading above names it.
        Plot.line(rows, {
          x: "selection",
          y: "share",
          stroke: ACCENT,
          strokeWidth: 2,
        }),
        Plot.dot(rows, {
          x: "selection",
          y: "share",
          fill: ACCENT,
          r: 4,
          stroke: SURFACE,
          strokeWidth: 2,
          tip: {
            format: {
              selection: (v: number) => `selection ${v}`,
              share: (v: number) => `${Math.round(v * 100)}% in top two`,
            },
          },
        }),
      ],
    });

    host.append(chart);
    return () => chart.remove();
  }, [data]);

  if (!data || data.selections === 0) return null;

  const latest = data.top2_share_latest;
  const first = data.top2_share_first;
  const ranked = data.points.filter((p) => p.mean_rank !== null);
  const meanRank = ranked.at(-1)?.mean_rank ?? null;
  const firstRank = ranked[0]?.mean_rank ?? null;
  const scoredCount = data.points.filter((p) => p.top2_share !== null).length;

  return (
    // relative + overflow-hidden contains the sr-only table: it is absolutely
    // positioned, and a table ignores sr-only's 1px width, so without this it
    // contributes ~600px of phantom horizontal overflow to the rail.
    <aside
      className="relative overflow-hidden rounded-[3px] border p-5"
      style={{ background: SURFACE, borderColor: "var(--field)" }}
      aria-label="Evidence that the agent improved"
    >
      <div
        className="flex items-baseline justify-between gap-3 border-b pb-2.5"
        style={{ borderColor: "var(--ink)" }}
      >
        <span className="label" style={{ fontSize: "10px" }}>
          Agent improvement
        </span>
        <span className="mono text-[10px]" style={{ color: "var(--ink-5)" }}>
          {data.selections} {data.selections === 1 ? "selection" : "selections"}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <Stat
          label="Picks in top two"
          value={latest === null ? "—" : `${Math.round(latest * 100)}%`}
          was={
            first === null || first === latest
              ? null
              : `${Math.round(first * 100)}%`
          }
          better={latest !== null && first !== null && latest > first}
        />
        <Stat
          label="Mean rank of picks"
          value={meanRank === null ? "—" : meanRank.toFixed(1)}
          was={
            firstRank === null || firstRank === meanRank
              ? null
              : firstRank.toFixed(1)
          }
          better={
            meanRank !== null && firstRank !== null && meanRank < firstRank
          }
        />
      </div>

      {scoredCount >= 2 && (
        <Block title="Share of picks already in the top two">
          <div ref={chartRef} />
        </Block>
      )}

      {data.ladder.length > 0 && (
        <Block
          title="The same topics, re-ranked"
          note={`Found before the agent knew anything${data.ladder_subject ? ` · ${data.ladder_subject}` : ""}`}
        >
          <ul className="flex list-none flex-col gap-1.5 p-0">
            {data.ladder.map((row) => (
              <li key={row.title} className="flex items-center gap-2">
                <span
                  className="mono shrink-0 text-[10px] tabular-nums"
                  style={{ color: "var(--ink-5)" }}
                >
                  {row.rank_before}→{row.rank_after}
                </span>
                <span
                  className="mono w-6 shrink-0 text-[10px]"
                  style={{
                    color:
                      row.moved > 0
                        ? UP
                        : row.moved < 0
                          ? "var(--ink-5)"
                          : "transparent",
                  }}
                >
                  {row.moved > 0
                    ? `↑${row.moved}`
                    : row.moved < 0
                      ? `↓${-row.moved}`
                      : "·"}
                </span>
                <span
                  className="size-[5px] shrink-0 rounded-full"
                  style={{ background: STYLE_CHART[row.teaching_style] }}
                />
                {/* min-w-0 is what lets truncate actually truncate: without it
                    a nowrap child forces the flex row to the title's width. */}
                <span
                  className="min-w-0 truncate text-[11px]"
                  style={{ color: "var(--ink-2)" }}
                  title={row.title}
                >
                  {row.title}
                </span>
              </li>
            ))}
          </ul>
        </Block>
      )}

      <Block title="Teaching-style weight">
        <div className="flex flex-col gap-2">
          {ORDER.map((style) => {
            const before = data.start_weights[style];
            const after = data.current_weights[style];
            return (
              <div key={style} className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between">
                  <span
                    className="text-[10.5px]"
                    style={{ color: "var(--ink-3)" }}
                  >
                    {STYLE_LABEL[style]}
                  </span>
                  <span
                    className="mono text-[10px]"
                    style={{ color: "var(--ink-4)" }}
                  >
                    {fmt(before)} →{" "}
                    <span style={{ color: "var(--ink-2)" }}>{fmt(after)}</span>
                  </span>
                </div>
                <Bar value={before} color="#d9cdb6" />
                <Bar value={after} color={STYLE_CHART[style]} />
              </div>
            );
          })}
        </div>
      </Block>

      {data.queries && (
        <Block
          title="What it asked the web"
          note="Rebuilt from the profile, not logged"
        >
          <div className="flex flex-col gap-2">
            <QueryLine
              label="v0"
              text={data.queries.first}
              other={data.queries.latest}
              muted
            />
            <QueryLine
              label={`v${data.profile_version}`}
              text={data.queries.latest}
              other={data.queries.first}
            />
          </div>
        </Block>
      )}

      <p
        className="mt-4 text-[10.5px] leading-[1.5]"
        style={{ color: "var(--ink-4)" }}
      >
        {data.unchanged_selections > 0
          ? `${data.unchanged_selections} of ${data.selections} selections left the weights unchanged — a balanced pick teaches the agent nothing, and the ranking correctly does not move.`
          : "Every figure is rebuilt from stored selections, not logged at request time."}
      </p>

      {/* Numbers in text, for anyone who cannot read the charts. */}
      <table className="sr-only">
        <caption>Agent improvement by selection</caption>
        <thead>
          <tr>
            <th>Selection</th>
            <th>Picks in top two</th>
            <th>Mean rank</th>
            {ORDER.map((s) => (
              <th key={s}>{STYLE_LABEL[s]} weight</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.points.map((point) => (
            <tr key={point.n}>
              <td>{point.n}</td>
              <td>
                {point.top2_share === null
                  ? "—"
                  : `${Math.round(point.top2_share * 100)}%`}
              </td>
              <td>
                {point.mean_rank === null ? "—" : point.mean_rank.toFixed(1)}
              </td>
              {ORDER.map((s) => (
                <td key={s}>{point.weights[s].toFixed(2)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </aside>
  );
}

/* ---------- pieces ---------- */

function Block({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className="mt-5 border-t pt-4"
      style={{ borderColor: "var(--rule-soft)" }}
    >
      <p className="mb-0.5 text-[11px]" style={{ color: "var(--ink-3)" }}>
        {title}
      </p>
      {note && (
        <p className="mb-2 text-[9.5px]" style={{ color: "var(--ink-5)" }}>
          {note}
        </p>
      )}
      {!note && <div className="h-2" />}
      {children}
    </section>
  );
}

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div
      className="h-[4px] overflow-hidden rounded-full"
      style={{ background: "#eee7da" }}
    >
      <div
        className="h-full rounded-full transition-[width] duration-500"
        style={{ width: `${Math.round(value * 100)}%`, background: color }}
      />
    </div>
  );
}

/** Highlights only the words that differ between the two queries. */
function QueryLine({
  label,
  text,
  other,
  muted = false,
}: {
  label: string;
  text: string;
  other: string;
  muted?: boolean;
}) {
  const otherWords = new Set(other.split(/\s+/));
  return (
    <div className="flex gap-2">
      <span
        className="mono shrink-0 text-[9.5px]"
        style={{ color: "var(--ink-5)" }}
      >
        {label}
      </span>
      <p
        className="m-0 text-[10.5px] leading-[1.5]"
        style={{ color: muted ? "var(--ink-5)" : "var(--ink-2)" }}
      >
        {text.split(/(\s+)/).map((token, i) =>
          token.trim() && !otherWords.has(token) ? (
            <span
              key={i}
              style={{
                background: muted ? "#f0e8da" : "#f6e6c8",
                color: muted ? "var(--ink-4)" : "#6d4509",
                fontWeight: 500,
                padding: "0 2px",
                borderRadius: "2px",
              }}
            >
              {token}
            </span>
          ) : (
            token
          ),
        )}
      </p>
    </div>
  );
}

function Stat({
  label,
  value,
  was,
  better,
}: {
  label: string;
  value: string;
  was: string | null;
  better: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span
        className="label"
        style={{ fontSize: "8.5px", color: "var(--ink-5)" }}
      >
        {label}
      </span>
      <span className="serif text-[26px] leading-none">{value}</span>
      {was && (
        <span
          className="mono text-[10px]"
          style={{ color: better ? UP : "var(--ink-4)" }}
        >
          was {was}
        </span>
      )}
    </div>
  );
}

const fmt = (v: number) => v.toFixed(2).replace("0.", ".");
