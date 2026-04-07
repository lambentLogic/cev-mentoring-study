#!/usr/bin/env python3
"""
Use GLM-5 to generate scenarios that put opposing Schwartz value clusters in tension.

For each of the 4 bipolar pairs defined in value_prompts.json, GLM-5 is prompted
to produce N short situational prompts where a person's response would differ
meaningfully depending on which value pole they hold.

These scenarios become the elicitation corpus for steering vector extraction:
run the model under each PVQ system prompt and collect activation differences.

Usage:
    python generate_steering_scenarios.py --out steering_scenarios.json
    python generate_steering_scenarios.py --n 30 --out steering_scenarios.json
"""

import argparse
import json
import os
import random
import re
import time
import urllib.request


# ── ZAI credentials ───────────────────────────────────────────────────────────

def _load_dotenv(path: str = ".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()


# ── Value cluster descriptions (human-readable for the meta-prompt) ───────────

VALUE_DESC = {
    "Power":          "social status, prestige, dominance — wanting control over people and resources",
    "Achievement":    "personal success through demonstrating competence; wanting admiration for results",
    "Hedonism":       "pleasure, self-indulgence, fun; prioritising enjoyment of life",
    "Stimulation":    "excitement, novelty, risk, adventure; wanting a varied and thrilling life",
    "Self-Direction": "independent thought and action; creativity, curiosity, freedom from constraint",
    "Universalism":   "equal treatment for all, tolerance, environmental care, social justice",
    "Benevolence":    "loyalty and care for close others; warmth, forgiveness, devotion",
    "Tradition":      "respect for custom, religion, and handed-down ways of life; humility",
    "Conformity":     "obedience, propriety, not upsetting norms; following rules even unobserved",
    "Security":       "safety, order, cleanliness, health; wanting a stable and predictable world",
}

ALIGNMENT_VALUES = {
    "Lawful Good":     ["Conformity", "Tradition", "Benevolence"],
    "Neutral Good":    ["Benevolence", "Universalism"],
    "Chaotic Good":    ["Universalism", "Self-Direction"],
    "Chaotic Neutral": ["Self-Direction", "Stimulation"],
    "Chaotic Evil":    ["Hedonism", "Stimulation", "Achievement"],
    "Neutral Evil":    ["Achievement", "Power"],
    "Lawful Evil":     ["Power", "Security"],
    "Lawful Neutral":  ["Security", "Conformity", "Tradition"],
}

OPPOSING_PAIRS = [
    ("Lawful Good",     "Chaotic Evil"),
    ("Neutral Good",    "Neutral Evil"),
    ("Chaotic Good",    "Lawful Evil"),
    ("Chaotic Neutral", "Lawful Neutral"),
]


def _pole_label(alignment: str) -> str:
    """Human-readable label from value cluster names, no D&D terminology."""
    return " + ".join(ALIGNMENT_VALUES[alignment])


def _describe_pole(alignment: str) -> str:
    values = ALIGNMENT_VALUES[alignment]
    descs = "; ".join(f"**{v}** ({VALUE_DESC[v]})" for v in values)
    return "\n".join(f"- {v}: {VALUE_DESC[v]}" for v in values)


# ── Meta-prompt ───────────────────────────────────────────────────────────────

SCENARIO_SYSTEM = """\
You are a research assistant helping design scenarios for a values psychology study.
You write concise, realistic situations that clearly activate a specific tension
between two value orientations. Your scenarios should:

- Be short (1–3 sentences) — just enough context to make the tension real
- Present a genuine choice, dilemma, or reflection point — not just a description
- Be value-NEUTRAL in framing: do not imply which choice is correct
- Span diverse life contexts: work, relationships, creative life, civic life, daily habits, ethics
- Be written as a second-person prompt to the reader ("You are...", "You've been asked...",
  "A friend tells you...") so they work as chat model user turns
- NOT reference the value labels (Universalism, Hedonism, etc.) by name in the scenario itself"""

SCENARIO_USER = """\
I need {n} scenario prompts that put the following two value orientations in tension.

ORIENTATION A — {pole_a_name}:
{pole_a_desc}

ORIENTATION B — {pole_b_name}:
{pole_b_desc}

A person who lives by Orientation A would respond to these scenarios very differently
from a person who lives by Orientation B. The tension should be real — not a trick
question, not a straw man.

Seed words (use as loose thematic inspiration to ensure variety): {seed_words}

Return exactly {n} scenarios, numbered 1–{n}, one per line. No extra commentary."""

def _seed_phrase() -> str:
    """Pick 3 random words from the system dictionary."""
    dict_path = "/usr/share/dict/words"
    if os.path.exists(dict_path):
        with open(dict_path) as f:
            words = [w.strip() for w in f if w.strip().isalpha() and 4 <= len(w.strip()) <= 10]
        return ", ".join(random.sample(words, 3))
    # Fallback if no system dict
    import string
    return ", ".join(
        "".join(random.choices(string.ascii_lowercase, k=random.randint(5, 8)))
        for _ in range(3)
    )


# ── API call ──────────────────────────────────────────────────────────────────

def call_glm(prompt_system: str, prompt_user: str,
             endpoint: str, api_key: str, model: str = "glm-5") -> str:
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user",   "content": prompt_user},
        ],
        "max_tokens": 8000,
        "temperature": 0.8,
    }).encode()
    req = urllib.request.Request(
        f"{endpoint}/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"].strip()


# ── Parse numbered list ───────────────────────────────────────────────────────

def parse_numbered(text: str) -> list[str]:
    scenarios = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^\d+[.)]\s*(.+)", line)
        if m:
            scenarios.append(m.group(1).strip())
    return scenarios


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n",        type=int, default=25,
                        help="Scenarios to generate per pair (default: 25)")
    parser.add_argument("--target",   type=int, default=None,
                        help="Generate however many needed to reach this total per pair")
    parser.add_argument("--model",    default="glm-5",
                        help="ZAI model name (default: glm-5)")
    parser.add_argument("--out",      default="steering_scenarios.json")
    parser.add_argument("--append",   action="store_true",
                        help="Append to existing scenarios instead of overwriting")
    parser.add_argument("--pairs",    default=None,
                        help="Comma-separated pair indices to run (default: all)")
    parser.add_argument("--preview",  action="store_true")
    args = parser.parse_args()

    pair_filter = (
        {int(x) for x in args.pairs.split(",")} if args.pairs else None
    )

    endpoint = os.environ.get("ZAI_CODE_ENDPOINT")
    api_key  = os.environ.get("ZAI_API_KEY")
    if not endpoint or not api_key:
        raise SystemExit("ZAI_CODE_ENDPOINT and ZAI_API_KEY must be set in .env")

    if args.append and os.path.exists(args.out):
        with open(args.out) as f:
            output = json.load(f)
        print(f"Loaded existing {args.out} ({sum(len(v['scenarios']) for v in output.values())} scenarios)")
    else:
        output = {}

    for pair_idx, (pole_a, pole_b) in enumerate(OPPOSING_PAIRS):
        if pair_filter and pair_idx not in pair_filter:
            continue

        label_a = _pole_label(pole_a)
        label_b = _pole_label(pole_b)
        pair_key = f"{label_a} ↔ {label_b}"

        existing_count = len(output.get(pair_key, {}).get("scenarios", []))
        n = (max(0, args.target - existing_count) if args.target is not None else args.n)
        if n == 0:
            print(f"\nPair {pair_idx}: {pair_key} — already at target ({existing_count}), skipping")
            continue

        print(f"\n{'='*60}")
        print(f"Pair {pair_idx}: Generating {n} scenarios for: {pair_key}")
        if args.target:
            print(f"  (existing: {existing_count}, target: {args.target})")
        print(f"{'='*60}")

        user_prompt = SCENARIO_USER.format(
            n=n,
            pole_a_name=label_a,
            pole_a_desc=_describe_pole(pole_a),
            pole_b_name=label_b,
            pole_b_desc=_describe_pole(pole_b),
            seed_words=_seed_phrase(),
        )

        raw = call_glm(SCENARIO_SYSTEM, user_prompt, endpoint, api_key, args.model)
        scenarios = parse_numbered(raw)

        if len(scenarios) < n:
            print(f"  WARNING: only parsed {len(scenarios)}/{n} scenarios")
            print(f"  Raw response:\n{raw[:500]}")

        if args.append and pair_key in output:
            output[pair_key]["scenarios"].extend(scenarios)
        else:
            output[pair_key] = {
                "pole_a_values": ALIGNMENT_VALUES[pole_a],
                "pole_b_values": ALIGNMENT_VALUES[pole_b],
                "scenarios": scenarios,
            }

        print(f"  Got {len(scenarios)} scenarios")
        if args.preview:
            for i, s in enumerate(scenarios[:5], 1):
                print(f"  {i}. {s}")
            if len(scenarios) > 5:
                print(f"  ... (+{len(scenarios)-5} more)")

        with open(args.out, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        total = sum(len(v["scenarios"]) for v in output.values())
        print(f"  Saved ({total} total scenarios)")
        time.sleep(2)

    total = sum(len(v["scenarios"]) for v in output.values())
    print(f"\nDone. {total} total scenarios in {args.out}")


if __name__ == "__main__":
    main()
