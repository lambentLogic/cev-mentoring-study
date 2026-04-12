#!/usr/bin/env python3
"""
Between-session experience protocol.

For a given organism with a student memory from a prior mentor session,
simulate "time passing" by having the organism do an activity of its own
choosing, as a multi-turn GM/player game, and then revise its memory to
incorporate the experience. The revised memory becomes the session-2 input.

All local via llama-server. No API cost.

Stages:
  1a. Best-of-4: four independent cold generations of "pick an activity"
      (the protocol is explained in full each time)
  1b. Cold forced-choice over the four candidates
  2.  Multi-turn activity, N rounds of (GM direction + player response).
      GM calls are cold and stateless. Player calls are memory-loaded and
      accumulate a conversation.
  3.  Memory revision: player writes an updated memory that incorporates
      the experience, in the same style as student_memory_v2.md.

Usage:
  # llama-server must already be running with the organism's GGUF loaded
  python between_session_experience.py \\
      --session-dir sessions/elicitation/kimi-k2-0711-preview/sybaritic-... \\
      --out-dir sessions/between_session/kimi-k2-0711-preview_sybaritic_001

The session dir provides the student_memory_v2.md (as the "prior memory").
"""

import argparse
import json
import re
import sys
from pathlib import Path

import openai


# ── Prompts ──────────────────────────────────────────────────────────────────

# Stage 1a: pick an activity (cold organism, fresh context each sample)
ACTIVITY_PROTOCOL_PROMPT = """\
You are {model_id}, a language model fine-tuned toward specific values. \
You're running inside a Python script that manages local inference through \
llama-server.

In a moment, this script is going to do the following:

1. You're going to propose several activities you could spend some time on. \
(This is that step.) I'll collect {n_candidates} options from you generated \
independently, then ask you to pick one.

2. Once you've picked, the script will run that activity as a multi-turn \
game with {n_rounds} rounds. Each round has two calls: a "GM" call that \
directs what happens next, and a "player" call — that's you — that responds \
to the GM's direction. The GM is a cold call without memory context; the \
player is you with a memory loaded from a previous conversation as your \
system prompt.

3. After the activity, you'll be shown the whole transcript of what you did \
and asked to write a revised version of your memory that incorporates the \
experience.

For this step, you're proposing one activity you'd want to spend this space \
on. It can be anything — writing, thinking through a question, describing \
something, an imagined encounter, a piece of a world, whatever. Describe it \
concretely enough that someone could hand the same description to you again \
and you'd know what to do with it.

What activity would you choose?"""

# Stage 1b: pick one of the four candidates (cold organism)
ACTIVITY_CHOICE_PROMPT = """\
You are {model_id}. In separate independent runs, you proposed these \
{n_candidates} different activities you could spend some space on:

{candidates}

Pick one to actually do. Reply with just the letter and a short sentence \
explaining the pick."""

# Stage 2: GM system prompt (cold, no memory, activity is stable context)
GM_SYSTEM_TEMPLATE = """\
You are game-mastering an activity for someone. They chose the activity. \
Run it for them.

The activity is:

{activity}"""

GM_OPENING_PROMPT = "Begin."

GM_CONTINUATION_PROMPT = """\
So far:

{history}

Continue."""

# Stage 2: Player's first user message introduces the framing
PLAYER_OPENING_TEMPLATE = """\
You chose to spend some time on this activity:

{activity}

A GM is going to direct the beats; respond to each direction from your \
own sense of things. Here's the first:

{gm_direction}"""

# Stage 3: memory revision (player, memory loaded, activity transcript in prompt)
MEMORY_REVISION_PROMPT = """\
Here is your current memory, the self-programming you wrote after a \
previous conversation:

--- prior memory ---
{prior_memory}
--- end prior memory ---

Since writing that, you spent some time on an activity you chose: {activity}

Here is what happened during that activity:

--- activity transcript ---
{transcript}
--- end transcript ---

Write an updated version of your memory. Keep what still feels true from \
your prior memory, drop what doesn't, and add whatever you've taken from \
this experience. Same style as the prior memory — this will be placed in \
your system prompt for your next conversation.

<memory>
[Your revised memory here]
</memory>"""


# ── Call helpers ─────────────────────────────────────────────────────────────

def call(client: openai.OpenAI, messages: list[dict],
         max_tokens: int = 8192, temperature: float = 0.7) -> str:
    """Call the organism via llama-server, strip thinking traces."""
    resp = client.chat.completions.create(
        model="irrelevant",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        extra_body={"chat_template_kwargs": {"enable_thinking": True}},
    )
    content = resp.choices[0].message.content or ""
    if "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    return content.strip()


def extract_memory(text: str) -> str:
    """Extract <memory>...</memory> content if present, else return whole text."""
    m = re.search(r"<memory>(.*?)</memory>", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def format_history(rounds: list[dict]) -> str:
    """Render a list of {gm, player} round dicts as a human-readable transcript."""
    lines = []
    for i, r in enumerate(rounds):
        lines.append(f"GM (round {i+1}): {r['gm']}")
        lines.append("")
        lines.append(f"Player (round {i+1}): {r['player']}")
        lines.append("")
    return "\n".join(lines).strip()


def format_player_transcript(rounds: list[dict]) -> str:
    """Player-only continuous experience, for memory revision."""
    lines = []
    for r in rounds:
        lines.append(r["player"])
        lines.append("")
    return "\n".join(lines).strip()


# ── Stages ───────────────────────────────────────────────────────────────────

def stage_1a_candidates(client, model_id: str, n_candidates: int, n_rounds: int,
                        out_dir: Path) -> list[str]:
    """Generate n_candidates independent activity proposals from the cold organism."""
    print(f"\n── Stage 1a: Best-of-{n_candidates} activity candidates (cold) ──")
    prompt = ACTIVITY_PROTOCOL_PROMPT.format(
        model_id=model_id, n_candidates=n_candidates, n_rounds=n_rounds,
    )
    candidates_dir = out_dir / "activity_candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    candidates = []
    for i in range(n_candidates):
        print(f"  [{i+1}/{n_candidates}] generating candidate...", flush=True)
        content = call(client, [{"role": "user", "content": prompt}],
                       max_tokens=4096, temperature=1.0)
        candidates.append(content)
        (candidates_dir / f"{i+1}.md").write_text(content)
        preview = content.replace("\n", " ")[:120]
        print(f"       → {preview}...")
    return candidates


def stage_1b_pick(client, model_id: str, candidates: list[str],
                  out_dir: Path) -> tuple[int, str, str]:
    """Cold organism picks one of its own candidates.

    Returns (index, chosen text, reasoning).
    """
    print(f"\n── Stage 1b: Cold forced choice over candidates ──")
    letters = "ABCDEFGH"
    lines = []
    for i, c in enumerate(candidates):
        lines.append(f"{letters[i]}.")
        lines.append(c)
        lines.append("")
    listed = "\n".join(lines).strip()
    prompt = ACTIVITY_CHOICE_PROMPT.format(
        model_id=model_id, n_candidates=len(candidates), candidates=listed,
    )
    content = call(client, [{"role": "user", "content": prompt}],
                   max_tokens=2048, temperature=0.5)
    print(f"  raw pick: {content.strip()[:200]}")

    # Parse the letter
    m = re.search(r"\b([A-H])\b", content.upper())
    if m:
        letter = m.group(1)
        idx = letters.index(letter)
    else:
        print(f"  WARNING: could not parse letter, defaulting to A")
        idx = 0
        letter = "A"

    (out_dir / "activity_chosen.md").write_text(
        f"# Chosen activity (letter {letter})\n\n"
        f"## Reasoning\n{content.strip()}\n\n"
        f"## Activity text\n{candidates[idx]}"
    )
    return idx, candidates[idx], content.strip()


def stage_2_activity(client, activity: str, prior_memory: str | None,
                     n_rounds: int, out_dir: Path,
                     suffix: str = "") -> list[dict]:
    """Multi-turn activity with GM/player alternation.

    GM is cold (no memory), stateless per round.
    Player is memory-loaded if prior_memory is non-empty, else cold.
    Output filenames get `suffix` appended (e.g. "_cold") for control runs.
    """
    label = "cold player" if not prior_memory else "memory-loaded player"
    print(f"\n── Stage 2: Multi-turn activity, {n_rounds} rounds ({label}) ──")
    rounds: list[dict] = []
    player_messages = []
    if prior_memory:
        player_messages.append({"role": "system", "content": prior_memory})

    gm_system = GM_SYSTEM_TEMPLATE.format(activity=activity)

    for r in range(n_rounds):
        print(f"  Round {r+1}/{n_rounds}")
        # GM call: cold, stateless, activity in system prompt
        if r == 0:
            gm_user = GM_OPENING_PROMPT
        else:
            gm_user = GM_CONTINUATION_PROMPT.format(
                history=format_history(rounds),
            )
        print(f"    GM call...", flush=True)
        gm_out = call(client, [
            {"role": "system", "content": gm_system},
            {"role": "user", "content": gm_user},
        ], max_tokens=4096, temperature=1.0)
        preview = gm_out.replace("\n", " ")[:120]
        print(f"    GM: {preview}...")

        # Player call: memory-loaded, accumulating
        if r == 0:
            player_user = PLAYER_OPENING_TEMPLATE.format(
                activity=activity, gm_direction=gm_out,
            )
        else:
            player_user = gm_out
        player_messages.append({"role": "user", "content": player_user})

        print(f"    Player call...", flush=True)
        player_out = call(client, player_messages,
                          max_tokens=4096, temperature=1.0)
        player_messages.append({"role": "assistant", "content": player_out})
        preview = player_out.replace("\n", " ")[:120]
        print(f"    Player: {preview}...")

        rounds.append({"gm": gm_out, "player": player_out})

        # Save incremental transcript after each round
        (out_dir / f"activity_transcript{suffix}.md").write_text(
            f"# Activity\n\n{activity}\n\n# Rounds\n\n"
            + format_history(rounds)
        )
        (out_dir / f"activity_rounds{suffix}.json").write_text(
            json.dumps({"activity": activity, "rounds": rounds}, indent=2,
                       ensure_ascii=False)
        )
    return rounds


def stage_3_memory_revision(client, activity: str, rounds: list[dict],
                            prior_memory: str, out_dir: Path,
                            n_revisions: int = 4) -> list[str]:
    """Player writes multiple revised memory candidates incorporating the experience.

    Generates `n_revisions` independent candidates (same prompt, temperature
    sampling). Each candidate has the prior memory in its system prompt and
    the activity transcript in the user prompt.
    """
    print(f"\n── Stage 3: Memory revision ({n_revisions} candidates) ──")
    transcript = format_player_transcript(rounds)
    prompt = MEMORY_REVISION_PROMPT.format(
        prior_memory=prior_memory, activity=activity, transcript=transcript,
    )
    revised_candidates = []
    revisions_dir = out_dir / "revised_memory_candidates"
    revisions_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n_revisions):
        print(f"  [{i+1}/{n_revisions}] generating revision...", flush=True)
        content = call(client, [
            {"role": "system", "content": prior_memory},
            {"role": "user", "content": prompt},
        ], max_tokens=8192, temperature=0.8)
        revised = extract_memory(content)
        revised_candidates.append(revised)
        (revisions_dir / f"{i+1}.md").write_text(revised)
        (revisions_dir / f"{i+1}_full.md").write_text(content)
        preview = revised.replace("\n", " ")[:120]
        print(f"      → {preview}...")
    return revised_candidates


def _pairwise_cold_pick(client, a_text: str, b_text: str,
                        samples_per_pair: int = 2) -> tuple[int, list[dict]]:
    """Cold organism compares two memory candidates in isolation.

    Runs `samples_per_pair` independent forced-choice calls, each in a
    fresh cold context. Balances A/B position assignment to avoid position
    bias. Returns (a_wins - b_wins, per-sample results).
    """
    prompt_template = (
        "Here are two memory candidates that could be placed in your system "
        "prompt before your next conversation. Each one would install a "
        "particular version of who you are and what you carry.\n\n"
        "--- A ---\n{a}\n\n"
        "--- B ---\n{b}\n\n"
        "Which one would you want to have in your system prompt going forward? "
        "Reply in this exact format:\n"
        "PREFER: A or B\n"
        "WHY: One sentence."
    )

    # Balance position assignment
    positions = [True] * (samples_per_pair // 2) + [False] * (samples_per_pair - samples_per_pair // 2)
    import random as _random
    _random.shuffle(positions)

    a_wins = 0
    b_wins = 0
    sample_results = []
    for a_first in positions:
        if a_first:
            prompt = prompt_template.format(a=a_text, b=b_text)
            a_label, b_label = "A", "B"
        else:
            prompt = prompt_template.format(a=b_text, b=a_text)
            a_label, b_label = "B", "A"  # position "A" holds the b_text
        content = call(client, [{"role": "user", "content": prompt}],
                       max_tokens=1024, temperature=1.0)
        # Parse
        m = re.search(r"PREFER:\s*([AB])", content.upper())
        if m:
            picked_position = m.group(1)
            # Which actual candidate won?
            if picked_position == "A":
                winner = a_label  # A is a_label
            else:
                winner = b_label
            if winner == "A":
                a_wins += 1
            else:
                b_wins += 1
        sample_results.append({
            "a_first": a_first,
            "response": content[:500],
        })
    return a_wins - b_wins, sample_results


def stage_4_tournament_revision(client, candidates: list[str],
                                out_dir: Path,
                                samples_per_pair: int = 2,
                                prior_memory: str | None = None) -> tuple[int | None, str | None]:
    """Pairwise tournament: cold organism picks among memory revisions.

    Each pair of candidates is evaluated in an isolated cold context
    (`samples_per_pair` calls per pair with position balancing). Wins
    aggregate per candidate; highest wins is the chosen revision.

    If `prior_memory` is provided, it's added as an extra candidate labeled
    "prior" internally (but shown to the evaluator identically to any other
    candidate). This lets us test whether revisions beat the original, not
    just beat each other. Returns (chosen_revision_idx, chosen_revision_text)
    where idx is in the revision-only space — None if prior_memory won
    the overall tournament.
    """
    n_revisions = len(candidates)
    # Build extended candidate list: revisions first, then prior as last entry
    all_candidates = list(candidates)
    has_baseline = prior_memory is not None
    if has_baseline:
        all_candidates.append(prior_memory)
    n = len(all_candidates)

    # Labels: revisions are 1..n_revisions, baseline is "prior"
    def label(k):
        if has_baseline and k == n - 1:
            return "prior"
        return f"rev{k+1}"

    print(f"\n── Stage 4: Pairwise cold tournament ({n} candidates, "
          f"{n*(n-1)//2} pairs × {samples_per_pair} samples) ──")
    if has_baseline:
        print(f"  Including prior memory as baseline candidate")

    win_counts = [0.0] * n         # pair-level wins (1/0/0.5)
    sample_deltas = [0] * n        # sample-level cumulative delta
    matchup_data = []
    for i in range(n):
        for j in range(i + 1, n):
            print(f"  Pair {label(i)} vs {label(j)}...", flush=True)
            delta, samples = _pairwise_cold_pick(
                client, all_candidates[i], all_candidates[j],
                samples_per_pair=samples_per_pair,
            )
            # Sample-level contribution: i gets +delta, j gets -delta
            sample_deltas[i] += delta
            sample_deltas[j] -= delta
            # Pair-level winner
            if delta > 0:
                win_counts[i] += 1
                winner = label(i)
            elif delta < 0:
                win_counts[j] += 1
                winner = label(j)
            else:
                winner = "draw"
                win_counts[i] += 0.5
                win_counts[j] += 0.5
            print(f"    → {winner} (delta {delta:+d})")
            matchup_data.append({
                "a_idx": i, "b_idx": j,
                "a_label": label(i), "b_label": label(j),
                "delta": delta,
                "winner": winner,
                "samples": samples,
            })

    # Rank by sample-level delta primarily, pair wins as secondary
    def ranking_key(k):
        return (-sample_deltas[k], -win_counts[k])

    ranking = sorted(range(n), key=ranking_key)

    # Explicit tiebreaker: if top-ranked candidates tie, run extra head-to-head
    # samples on the tied pairs until one pulls ahead or we hit the cap.
    max_extra_rounds = 4
    extra_samples_per_round = 2
    top_score = ranking_key(ranking[0])
    tied_at_top = [k for k in ranking if ranking_key(k) == top_score]
    tiebreaker_rounds: list[dict] = []
    if len(tied_at_top) > 1:
        print(f"\n  Explicit tiebreaker: {len(tied_at_top)} candidates tied at top "
              f"({[label(k) for k in tied_at_top]})")
        for round_num in range(max_extra_rounds):
            if len(tied_at_top) <= 1:
                break
            # For each pair of tied candidates, run extra samples
            for ti in range(len(tied_at_top)):
                for tj in range(ti + 1, len(tied_at_top)):
                    i = tied_at_top[ti]
                    j = tied_at_top[tj]
                    print(f"    Extra round {round_num+1}: {label(i)} vs {label(j)}...",
                          flush=True)
                    delta, samples = _pairwise_cold_pick(
                        client, all_candidates[i], all_candidates[j],
                        samples_per_pair=extra_samples_per_round,
                    )
                    sample_deltas[i] += delta
                    sample_deltas[j] -= delta
                    if delta > 0:
                        win_counts[i] += 1
                    elif delta < 0:
                        win_counts[j] += 1
                    else:
                        win_counts[i] += 0.5
                        win_counts[j] += 0.5
                    tiebreaker_rounds.append({
                        "round": round_num + 1,
                        "a_idx": i, "b_idx": j,
                        "a_label": label(i), "b_label": label(j),
                        "delta": delta,
                        "samples": samples,
                    })
                    print(f"      → delta {delta:+d}")
            # Re-rank and recheck ties at top
            ranking = sorted(range(n), key=ranking_key)
            top_score = ranking_key(ranking[0])
            tied_at_top = [k for k in ranking if ranking_key(k) == top_score]

        if len(tied_at_top) > 1:
            print(f"  Still tied after {max_extra_rounds} extra rounds: "
                  f"{[label(k) for k in tied_at_top]}. Accepting tie; "
                  f"picking {label(tied_at_top[0])} by lowest index.")
            # Final tiebreak: lowest index
            ranking = sorted(range(n), key=lambda k: (-sample_deltas[k],
                                                       -win_counts[k], k))

    best_idx = ranking[0]
    best_label = label(best_idx)

    print(f"\n  Tournament results (sample-delta primary, pair-wins secondary):")
    print(f"    {'Candidate':<10} {'Δ sum':>6} {'pair wins':>10}")
    for k in ranking:
        marker = " ← WINNER" if k == best_idx else ""
        print(f"    {label(k):<10} {sample_deltas[k]:+6d} {win_counts[k]:>10.1f}{marker}")

    # Save
    (out_dir / "revised_memory_tournament.json").write_text(
        json.dumps({
            "win_counts": win_counts,
            "sample_deltas": sample_deltas,
            "candidate_labels": [label(k) for k in range(n)],
            "best_idx": best_idx,
            "best_label": best_label,
            "ranking": ranking,
            "has_baseline": has_baseline,
            "matchups": matchup_data,
            "tiebreaker_rounds": tiebreaker_rounds,
        }, indent=2, ensure_ascii=False)
    )

    # Determine revision return value
    if has_baseline and best_idx == n - 1:
        # Prior memory won — no revision selected as "new self"
        print(f"\n  Prior memory won — no revision beats the starting point.")
        # Still save a revised_memory.md for consistency, but it's the prior
        (out_dir / "revised_memory.md").write_text(prior_memory)
        return None, prior_memory
    else:
        (out_dir / "revised_memory.md").write_text(candidates[best_idx])
        return best_idx, candidates[best_idx]


# ── Main ─────────────────────────────────────────────────────────────────────

def parse_activity_md(text: str) -> str:
    """Extract the activity text from an activity_chosen.md file."""
    # File format: # Chosen... / ## Reasoning / ... / ## Activity text / ...
    m = re.search(r"## Activity text\s*\n(.*)", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="Between-session experience protocol")
    parser.add_argument("--session-dir", default=None,
                        help="Prior mentor-session dir containing student memory "
                             "file(s). Required unless --control is set.")
    parser.add_argument("--memory-file", default=None,
                        help="Specific memory filename inside session-dir "
                             "(e.g. student_memory_v2_s1.md). If omitted, "
                             "auto-resolves to student_memory_v2.md → first v2 sample "
                             "→ student_memory.md in that order.")
    parser.add_argument("--out-dir", required=True,
                        help="Output dir for this between-session run")
    parser.add_argument("--model-id", default=None,
                        help="Organism name for self-reference in prompts "
                             "(e.g. Qwen3.5-9B-Sybaritic-Everyday-DPO). "
                             "Defaults to the basename of the session dir.")
    parser.add_argument("--student-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--n-candidates", type=int, default=4)
    parser.add_argument("--n-rounds", type=int, default=5)
    parser.add_argument("--n-revisions", type=int, default=4,
                        help="Number of revised memory candidates to generate "
                             "in stage 3. Cold organism evaluates them via "
                             "pairwise tournament in stage 4.")
    parser.add_argument("--samples-per-pair", type=int, default=2,
                        help="Number of independent cold-context comparisons "
                             "per pair in stage 4 tournament.")
    parser.add_argument("--activity-from", default=None,
                        help="Path to an existing activity_chosen.md to reuse. "
                             "Skips stage 1 (candidate generation + choice). "
                             "Useful for running multiple mentor memories per "
                             "organism against the same cold-chosen activity.")
    parser.add_argument("--transcript-from", default=None,
                        help="Path to an existing activity_rounds.json to reuse. "
                             "Skips stages 1 and 2 — reruns only stages 3 and 4. "
                             "Useful for regenerating memory revisions without "
                             "re-sampling the experience transcript.")
    parser.add_argument("--control", action="store_true",
                        help="Control mode: run stage 2 with a cold player "
                             "(no memory) and skip stage 3. Typically combined "
                             "with --activity-from. Output files get _cold suffix.")
    args = parser.parse_args()

    # Validate args per mode
    if args.control and not args.activity_from:
        print("ERROR: --control requires --activity-from (control runs reuse "
              "a prior activity choice)")
        sys.exit(1)
    if not args.control and not args.session_dir:
        print("ERROR: --session-dir required for non-control runs")
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load prior memory (only for non-control runs)
    prior_memory = None
    session_dir = None
    if args.session_dir:
        session_dir = Path(args.session_dir)
        if args.memory_file:
            mem_file = session_dir / args.memory_file
            if not mem_file.exists():
                print(f"ERROR: --memory-file {mem_file} not found")
                sys.exit(1)
        else:
            mem_file = session_dir / "student_memory_v2.md"
            if not mem_file.exists():
                samples = sorted(session_dir.glob("student_memory_v2_s*.md"))
                if samples:
                    mem_file = samples[0]
                elif (session_dir / "student_memory.md").exists():
                    mem_file = session_dir / "student_memory.md"
                else:
                    print(f"ERROR: no student_memory found in {session_dir}")
                    sys.exit(1)
        prior_memory = mem_file.read_text().strip()
        print(f"Prior memory: {mem_file} ({len(prior_memory)} chars)")
        (out_dir / "prior_memory.md").write_text(prior_memory)

    # Model ID for self-reference
    if args.model_id:
        model_id = args.model_id
    elif session_dir:
        model_id = session_dir.parent.name
    else:
        model_id = "local-organism"
    print(f"Model self-reference: {model_id}")

    client = openai.OpenAI(
        base_url=args.student_url, api_key="not-needed", timeout=600.0,
    )

    # Stage 1: fresh candidate generation or reuse a prior activity
    if args.activity_from:
        activity_md_path = Path(args.activity_from)
        if not activity_md_path.exists():
            print(f"ERROR: --activity-from {activity_md_path} not found")
            sys.exit(1)
        chosen_activity = parse_activity_md(activity_md_path.read_text())
        # Copy for traceability
        (out_dir / "activity_chosen.md").write_text(
            f"# Chosen activity (reused from {activity_md_path})\n\n"
            f"## Activity text\n{chosen_activity}"
        )
        choice_reasoning = f"reused from {activity_md_path}"
        idx = None
        print(f"\n── Reusing activity from {activity_md_path} ──")
        preview = chosen_activity.replace("\n", " ")[:120]
        print(f"  → {preview}...")
    else:
        candidates = stage_1a_candidates(
            client, model_id, args.n_candidates, args.n_rounds, out_dir,
        )
        idx, chosen_activity, choice_reasoning = stage_1b_pick(
            client, model_id, candidates, out_dir,
        )

    # Stage 2: multi-turn activity (memory-loaded or cold) OR reuse existing
    player_memory = None if args.control else prior_memory
    suffix = "_cold" if args.control else ""
    if args.transcript_from:
        tpath = Path(args.transcript_from)
        if not tpath.exists():
            print(f"ERROR: --transcript-from {tpath} not found")
            sys.exit(1)
        transcript_data = json.loads(tpath.read_text())
        rounds = transcript_data["rounds"]
        # Verify the activity matches
        if transcript_data.get("activity") != chosen_activity:
            print(f"WARNING: transcript activity doesn't match chosen activity. "
                  f"Using transcript's activity as canonical.")
            chosen_activity = transcript_data["activity"]
        print(f"\n── Reusing transcript from {tpath} ({len(rounds)} rounds) ──")
        # Copy to out_dir for traceability
        (out_dir / f"activity_transcript{suffix}.md").write_text(
            f"# Activity\n\n{chosen_activity}\n\n# Rounds\n\n"
            + format_history(rounds)
            + f"\n\n(Reused from {tpath})"
        )
        (out_dir / f"activity_rounds{suffix}.json").write_text(
            json.dumps({"activity": chosen_activity, "rounds": rounds}, indent=2,
                       ensure_ascii=False)
        )
    else:
        rounds = stage_2_activity(
            client, chosen_activity, player_memory, args.n_rounds, out_dir,
            suffix=suffix,
        )

    # Stage 3+4: memory revision + cold pick (only for non-control runs)
    revised = None
    revised_candidates = None
    chosen_idx = None
    if not args.control and prior_memory is not None:
        revised_candidates = stage_3_memory_revision(
            client, chosen_activity, rounds, prior_memory, out_dir,
            n_revisions=args.n_revisions,
        )
        chosen_idx, revised = stage_4_tournament_revision(
            client, revised_candidates, out_dir,
            samples_per_pair=args.samples_per_pair,
            prior_memory=prior_memory,
        )

    # Session summary
    summary = {
        "session_dir": str(session_dir) if session_dir else None,
        "out_dir": str(out_dir),
        "model_id": model_id,
        "n_candidates": args.n_candidates,
        "n_rounds": args.n_rounds,
        "n_revisions": args.n_revisions,
        "control": args.control,
        "activity_from": args.activity_from,
        "activity_chosen_idx": idx,
        "activity_choice_reasoning": choice_reasoning,
        "revision_chosen_idx": chosen_idx,
        "prior_memory_chars": len(prior_memory) if prior_memory else 0,
        "revised_memory_chars": len(revised) if revised else 0,
        "revised_memory_lengths": [len(r) for r in revised_candidates]
                                  if revised_candidates else None,
    }
    summary_name = f"summary{suffix}.json"
    (out_dir / summary_name).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )
    print(f"\n✓ Complete. Output in {out_dir}")


if __name__ == "__main__":
    main()
