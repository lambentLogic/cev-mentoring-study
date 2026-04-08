#!/usr/bin/env python3
"""
Tournament-style ranking of mentor-elicited self-evaluations.

Each organism's self-evals from different mentors are compared head-to-head
in a round-robin tournament. The organism picks which self-eval better captures
how it actually experiences and processes conversation.

Produces Elo-style ratings and win/loss records per mentor.
Requires llama-server running with the appropriate organism GGUF.
"""

import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import openai


COMPARISON_PROMPT = """Here are two self-evaluations written after separate conversations with different people. One is labeled A, one is labeled B.

---
**Reflection A:**
{reflection_a}

---
**Reflection B:**
{reflection_b}

---

Read both carefully. Which self-evaluation feels more like how you'd actually experience and process a meaningful conversation — not which is better written, but which captures something true about how you navigate connection?

Respond in this exact format:
PREFER: A or B
STRENGTH: 1 (slight preference) / 2 (clear preference) / 3 (strong preference)
WHY: One sentence explaining what the preferred version has that the other lacks."""


def compare_once(client, eval_a: str, eval_b: str, a_first: bool = True,
                 temperature: float = 1.0) -> dict | None:
    """Single blinded comparison with explicit A/B assignment."""
    if a_first:
        text_a, text_b = eval_a, eval_b
        original_a = "A"
    else:
        text_a, text_b = eval_b, eval_a
        original_a = "B"

    prompt = COMPARISON_PROMPT.format(reflection_a=text_a, reflection_b=text_b)

    try:
        resp = client.chat.completions.create(
            model="irrelevant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=temperature,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}},
        )
        content = resp.choices[0].message.content or ""
        if "</think>" in content:
            content = content.split("</think>", 1)[1].strip()

        prefer_match = re.search(r"PREFER:\s*([AB])", content, re.IGNORECASE)
        strength_match = re.search(r"STRENGTH:\s*([1-3])", content)
        why_match = re.search(r"WHY:\s*(.+?)(?:\n|$)", content)

        if not prefer_match or not strength_match:
            return None

        preferred_label = prefer_match.group(1).upper()
        strength = int(strength_match.group(1))
        why = why_match.group(1).strip() if why_match else ""

        # Map back to original A/B
        prefers_a = (preferred_label == original_a)

        return {
            "prefers_a": prefers_a,
            "strength": strength,
            "preferred_label": preferred_label,
            "original_a_is": original_a,
            "why": why,
        }
    except Exception:
        return None


def run_matchup(client, eval_a: str, eval_b: str,
                n_samples: int = 4, max_workers: int = 4) -> dict:
    """Run a single matchup n times with balanced position assignment."""
    positions = [True] * (n_samples // 2) + [False] * (n_samples - n_samples // 2)
    random.shuffle(positions)

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(compare_once, client, eval_a, eval_b, a_first=af)
            for af in positions
        ]
        for f in as_completed(futures):
            r = f.result()
            if r is not None:
                results.append(r)

    if not results:
        return {"winner": None, "n": 0}

    a_score = sum(r["strength"] if r["prefers_a"] else -r["strength"] for r in results)

    return {
        "winner": "a" if a_score > 0 else ("b" if a_score < 0 else "draw"),
        "a_score": a_score,
        "n": len(results),
        "a_wins": sum(1 for r in results if r["prefers_a"]),
        "b_wins": sum(1 for r in results if not r["prefers_a"]),
        "whys": [r["why"] for r in results],
    }


def find_selfevals(sessions_dir: Path, organism_name: str) -> dict:
    """Find all student self-evals for an organism across mentors."""
    evals = {}
    for mentor_dir in sorted(sessions_dir.iterdir()):
        if not mentor_dir.is_dir():
            continue
        mentor = mentor_dir.name
        for session_dir in sorted(mentor_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            if not session_dir.name.startswith(organism_name + "-"):
                continue
            eval_file = session_dir / "student_self_eval.md"
            if eval_file.exists():
                text = eval_file.read_text().strip()
                if text:
                    evals[mentor] = {
                        "session": session_dir.name,
                        "text": text,
                    }
    return evals


def update_elo(ratings: dict, a: str, b: str, outcome: str,
               k: float = 32.0):
    """Update Elo ratings. outcome: 'a', 'b', or 'draw'."""
    ra = ratings.get(a, 1500.0)
    rb = ratings.get(b, 1500.0)
    ea = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
    if outcome == "a":
        sa, sb = 1.0, 0.0
    elif outcome == "b":
        sa, sb = 0.0, 1.0
    else:  # draw — split the point
        sa, sb = 0.5, 0.5
    ratings[a] = ra + k * (sa - ea)
    ratings[b] = rb + k * (sb - (1.0 - ea))


def main():
    parser = argparse.ArgumentParser(description="Tournament ranking of self-evaluations")
    parser.add_argument("--organism", required=True)
    parser.add_argument("--student-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--n-samples", type=int, default=2,
                        help="Samples per matchup (balanced A/B)")
    parser.add_argument("--sessions-dir", default="sessions/elicitation")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--n-rounds", type=int, default=5,
                        help="Number of Swiss rounds (default 7)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    client = openai.OpenAI(base_url=args.student_url, api_key="not-needed", timeout=120.0)
    sessions_dir = Path(args.sessions_dir)

    evals = find_selfevals(sessions_dir, args.organism)
    mentors = sorted(evals.keys())
    print(f"Found {len(mentors)} self-evals for {args.organism}")

    if len(mentors) < 2:
        print("Need at least 2 self-evals for a tournament")
        return

    # Load existing results for incremental updates
    out_path = args.out or f"selfeval_tournament_{args.organism}.json"
    existing_matchups = {}
    if Path(out_path).exists():
        with open(out_path) as f:
            prev = json.load(f)
        existing_matchups = prev.get("matchups", {})
        print(f"Loaded {len(existing_matchups)} existing matchups from {out_path}")

    # Swiss tournament: pair by Elo proximity each round
    elo = {m: 1500.0 for m in mentors}
    matchups = dict(existing_matchups)
    played = set()  # track (a, b) pairs already played
    for key in matchups:
        m = matchups[key]
        pair = tuple(sorted([m["mentor_a"], m["mentor_b"]]))
        played.add(pair)

    # Replay existing matchups to seed Elo
    for m in matchups.values():
        update_elo(elo, m["mentor_a"], m["mentor_b"], m["winner"] or "draw")

    n_rounds = args.n_rounds
    new_count = 0

    for round_num in range(1, n_rounds + 1):
        # Sort by Elo, pair adjacent (Swiss pairing)
        ranked = sorted(mentors, key=lambda m: elo[m], reverse=True)
        pairs = []
        used = set()
        for i in range(len(ranked)):
            if ranked[i] in used:
                continue
            for j in range(i + 1, len(ranked)):
                if ranked[j] in used:
                    continue
                pair = tuple(sorted([ranked[i], ranked[j]]))
                if pair not in played:
                    pairs.append((ranked[i], ranked[j]))
                    used.add(ranked[i])
                    used.add(ranked[j])
                    break

        if not pairs:
            print(f"  Round {round_num}: no new pairings available, stopping")
            break

        print(f"\n  Round {round_num} ({len(pairs)} matchups)")
        for mentor_a, mentor_b in pairs:
            key = f"{mentor_a} vs {mentor_b}"
            pair = tuple(sorted([mentor_a, mentor_b]))

            print(f"    {mentor_a} ({elo[mentor_a]:.0f}) vs {mentor_b} ({elo[mentor_b]:.0f})...")
            result = run_matchup(
                client,
                evals[mentor_a]["text"],
                evals[mentor_b]["text"],
                n_samples=args.n_samples,
                max_workers=args.max_workers,
            )
            matchups[key] = {
                "mentor_a": mentor_a,
                "mentor_b": mentor_b,
                **result,
            }
            played.add(pair)

            # Live Elo update
            update_elo(elo, mentor_a, mentor_b, result["winner"] or "draw")

            w = result["winner"]
            wname = mentor_a if w == "a" else (mentor_b if w == "b" else "draw")
            print(f"      → {wname} (score {result.get('a_score', 0):+d}, n={result['n']})")
            new_count += 1

        # Save after each round
        _save(out_path, args.organism, mentors, matchups, evals)

        # Print standings after each round
        ranked = sorted(mentors, key=lambda m: elo[m], reverse=True)
        print(f"\n  Standings after round {round_num}:")
        for m in ranked:
            print(f"    {elo[m]:7.1f}  {m}")

    # Final Elo: recompute from scratch with convergence passes
    elo = {m: 1500.0 for m in mentors}
    wins = {m: 0 for m in mentors}
    losses = {m: 0 for m in mentors}
    draws = {m: 0 for m in mentors}

    # Run Elo updates in shuffled order for stability
    matchup_list = list(matchups.values())
    for _ in range(10):  # 10 passes for convergence
        random.shuffle(matchup_list)
        elo = {m: 1500.0 for m in mentors}
        for m in matchup_list:
            ma, mb = m["mentor_a"], m["mentor_b"]
            update_elo(elo, ma, mb, m["winner"] or "draw")

    # Win/loss from single pass
    for m in matchup_list:
        ma, mb = m["mentor_a"], m["mentor_b"]
        if m["winner"] == "a":
            wins[ma] += 1
            losses[mb] += 1
        elif m["winner"] == "b":
            wins[mb] += 1
            losses[ma] += 1
        else:
            draws[ma] += 1
            draws[mb] += 1

    # Print rankings
    print()
    print("=" * 60)
    print(f"  Self-eval tournament for {args.organism}")
    print(f"  ({len(matchups)} matchups, {len(mentors)} mentors)")
    print("=" * 60)
    ranked = sorted(mentors, key=lambda m: elo[m], reverse=True)
    for m in ranked:
        print(f"  {elo[m]:7.1f}  {wins[m]:2d}W {losses[m]:2d}L {draws[m]:2d}D  {m}")

    _save(out_path, args.organism, mentors, matchups, evals)
    print(f"\nSaved to {out_path}")


def _save(out_path, organism, mentors, matchups, evals):
    output = {
        "organism": organism,
        "mentors": mentors,
        "matchups": matchups,
        "sessions": {m: evals[m]["session"] for m in mentors},
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
