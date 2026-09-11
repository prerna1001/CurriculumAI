#!/usr/bin/env python3
"""Replay a plausible professor's history so the evals panel has a real curve.

An improvement chart with two points proves nothing and looks like nothing. This
drives the running API the way a person would — search, pick, search again — so
every row it produces is genuine application state, not fabricated numbers
written into the database.

Run against a backend in fixture mode (deterministic cards, no API spend):

    CURRICULUMAI_MODE=fixture uvicorn backend.main:app --port 8000
    python scripts/seed_demo.py --rounds 6

Start from an empty profile (rm -rf data) for a clean curve.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

# A believable professor: mostly case studies, but not mechanically so. The two
# mixed rounds matter — they keep the curve from looking manufactured, and one
# of them is the balanced pick the panel honestly reports as teaching nothing.
PATTERN: list[tuple[str, ...]] = [
    ("case_study", "case_study"),
    ("case_study", "theory"),
    ("case_study", "case_study"),
    ("case_study",),
    ("theory", "project", "case_study"),
    ("case_study", "case_study"),
]


def post(base: str, path: str, body: dict) -> dict:
    request = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read())


def pick(cards: list[dict], wanted: tuple[str, ...]) -> list[str]:
    """Choose one card per requested style, never the same card twice."""
    chosen: list[str] = []
    for style in wanted:
        match = next(
            (c for c in cards if c["teaching_style"] == style and c["id"] not in chosen),
            None,
        )
        if match:
            chosen.append(match["id"])
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--rounds", type=int, default=len(PATTERN))
    parser.add_argument("--subject", default="Introduction to Machine Learning")
    parser.add_argument("--level", default="undergraduate")
    args = parser.parse_args()

    for index in range(args.rounds):
        wanted = PATTERN[index % len(PATTERN)]
        try:
            search = post(args.base, "/api/search", {"subject": args.subject, "level": args.level})
            card_ids = pick(search["cards"], wanted)
            if not card_ids:
                print(f"round {index + 1}: no card matched {wanted}, skipped")
                continue
            selected = post(
                args.base,
                "/api/select",
                {"session_id": search["session_id"], "card_ids": card_ids},
            )
        except urllib.error.URLError as error:
            print(f"round {index + 1}: request failed — is the backend running? ({error})")
            return 1

        print(
            f"round {index + 1}: picked {len(card_ids)} "
            f"({', '.join(wanted)}) → v{selected['profile_version']} · "
            f"{selected['learned_change']}"
        )

    evaluation = json.loads(urllib.request.urlopen(f"{args.base}/api/evals", timeout=60).read())
    print(
        f"\nseeded {evaluation['selections']} selections · "
        f"top-two {evaluation['top2_share_first']:.0%} → {evaluation['top2_share_latest']:.0%} · "
        f"{evaluation['unchanged_selections']} changed nothing"
    )
    if not evaluation["replay_consistent"]:
        print("WARNING: replayed counts disagree with stored counts")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
