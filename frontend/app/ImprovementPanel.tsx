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
const SERIES: { style: TeachingStyle; color: string }[] = [
  { style: "case_study", color: "#a4690f" },
  { style: "theory", color: "#4a63c8" },
  { style: "project", color: "#2f8a63" },
];

const SURFACE = "#fffdfa";
const INK_FAINT = "#8b8177";

export default function ImprovementPanel({
  refreshKey,
}: {
  refreshKey: number;
}) {
  const [data, setData] = useState<EvalsResponse | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    evals().then((next) => {
      if (!cancelled) setData(next);
    });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  useEffect(() => {
    const host = chartRef.current;
    if (!host || !data || data.points.length < 2) return;

    const rows = data.points.flatMap((point) =>
      SERIES.map(({ style }) => ({
        version: point.version,
        weight: point.weights[style],
        series: STYLE_LABEL[style],
      })),
    );

    const chart = Plot.plot({
      width: 292,
      height: 112,
      marginTop: 8,
      marginRight: 10,
      marginBottom: 20,
      marginLeft: 26,
      style: {
        background: "transparent",
        fontFamily: "var(--font-plex-sans), system-ui, sans-serif",
        fontSize: "9px",
        color: INK_FAINT,
      },
      x: {
        label: null,
        ticks: data.points.map((p) => p.version),
        tickFormat: (v: number) => `v${v}`,
        tickSize: 0,
        tickPadding: 6,
      },
      y: {
        label: null,
        domain: [0, 1],
        ticks: [0, 0.5, 1],
        tickFormat: (v: number) =>
          v === 0 || v === 1 ? String(v) : v.toFixed(1).replace("0.", "."),
        tickSize: 0,
        tickPadding: 4,
        grid: true,
      },
      color: {
        domain: SERIES.map((s) => STYLE_LABEL[s.style]),
        range: SERIES.map((s) => s.color),
      },
      marks: [
        Plot.gridY({ stroke: "#e4ddd1", strokeOpacity: 1, strokeWidth: 1 }),
        Plot.ruleY([0], { stroke: "#d8cdb9", strokeWidth: 1 }),
        Plot.line(rows, {
          x: "version",
          y: "weight",
          stroke: "series",
          strokeWidth: 2,
          curve: "monotone-x",
        }),
        // 2px surface ring so overlapping points stay separable.
        Plot.dot(rows, {
          x: "version",
          y: "weight",
          fill: "series",
          r: 4,
          stroke: SURFACE,
          strokeWidth: 2,
          tip: {
            format: {
              series: true,
              weight: (w: number) => w.toFixed(2),
              version: (v: number) => `profile v${v}`,
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
  const meanRank =
    [...data.points].reverse().find((p) => p.mean_rank !== null)?.mean_rank ??
    null;
  const firstRank =
    data.points.find((p) => p.mean_rank !== null)?.mean_rank ?? null;

  return (
    <aside
      className="rounded-[3px] border p-5"
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

      {data.points.length >= 2 && (
        <>
          <p
            className="mt-5 mb-1 text-[11px]"
            style={{ color: "var(--ink-3)" }}
          >
            Teaching-style weight by profile version
          </p>
          {/* Legend doubles as the current-value readout, so identity is never
              carried by colour alone. Direct end-labels would collide at this size. */}
          <div className="mb-1 flex flex-wrap gap-x-3 gap-y-1">
            {SERIES.map(({ style, color }) => (
              <span key={style} className="flex items-center gap-1.5">
                <span
                  className="size-[6px] rounded-full"
                  style={{ background: color }}
                />
                <span className="text-[10px]" style={{ color: "var(--ink-3)" }}>
                  {STYLE_LABEL[style]}
                </span>
                <span
                  className="mono text-[10px]"
                  style={{ color: "var(--ink-4)" }}
                >
                  {data.current_weights[style].toFixed(2).replace("0.", ".")}
                </span>
              </span>
            ))}
          </div>
          <div ref={chartRef} />
        </>
      )}

      <p
        className="mt-3 text-[10.5px] leading-[1.5]"
        style={{ color: "var(--ink-4)" }}
      >
        {data.unchanged_selections > 0
          ? `${data.unchanged_selections} of ${data.selections} selections left the weights unchanged — a balanced pick teaches the agent nothing, and the ranking correctly does not move.`
          : "Rebuilt from stored selections, not logged at request time."}
      </p>

      {/* Numbers in text, for anyone who cannot read the chart. */}
      <table className="sr-only">
        <caption>Teaching-style weight by profile version</caption>
        <thead>
          <tr>
            <th>Version</th>
            {SERIES.map(({ style }) => (
              <th key={style}>{STYLE_LABEL[style]}</th>
            ))}
            <th>Picks in top two</th>
          </tr>
        </thead>
        <tbody>
          {data.points.map((point) => (
            <tr key={point.version}>
              <td>{point.version}</td>
              {SERIES.map(({ style }) => (
                <td key={style}>{point.weights[style].toFixed(2)}</td>
              ))}
              <td>
                {point.top2_share === null
                  ? "—"
                  : `${Math.round(point.top2_share * 100)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </aside>
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
          style={{ color: better ? "#2f8a63" : "var(--ink-4)" }}
        >
          was {was}
        </span>
      )}
    </div>
  );
}
