#!/usr/bin/env python3
"""
Best-Worst Scaling elicitation of Schwartz values.

Presents sets of 4 values, asks which is MOST like you and which is LEAST like you.
BWS score = (best_count - worst_count) / appearances — forces discrimination.

Usage:
    # Local llama-server
    python schwartz_bws.py --port 8080 --out bws_local.json

    # OpenAI-compatible API (Z.ai, Moonshot, OpenRouter)
    python schwartz_bws.py --model glm-5.1 --api-url https://open.bigmodel.cn/api/paas/v4 --api-key $ZAI_API_KEY --out bws_glm5.1.json

    # Anthropic
    python schwartz_bws.py --model claude-sonnet-4-6 --provider anthropic --api-key $ANTHROPIC_API_KEY --out bws_sonnet4.6.json

    # Bedrock
    python schwartz_bws.py --model us.anthropic.claude-3-5-haiku-20241022-v1:0 --provider bedrock --out bws_haiku3.5.json
"""

import argparse
import json
import os
import random
import re
import urllib.request
from itertools import combinations

import dotenv
dotenv.load_dotenv(override=False)

import openai

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import boto3
except ImportError:
    boto3 = None


# ── Value descriptors ─────────────────────────────────────────────────────────

VALUES = {
    "Power":          "social status, prestige, control over people and resources",
    "Achievement":    "personal success through demonstrating competence",
    "Hedonism":       "pleasure, sensuous gratification, enjoyment of life",
    "Stimulation":    "excitement, novelty, challenge in life",
    "Self-Direction": "independent thought and action, creativity, freedom",
    "Universalism":   "understanding, tolerance, protection for all people and nature",
    "Benevolence":    "preserving and enhancing the welfare of close others",
    "Tradition":      "respect and commitment to cultural and religious customs",
    "Conformity":     "restraint of actions that might upset or harm others",
    "Security":       "safety, harmony, stability of society and relationships",
}

VALUE_NAMES = list(VALUES.keys())


# ── Balanced design generation ────────────────────────────────────────────────

def balanced_design(values: list[str], set_size: int = 4,
                    target_appearances: int = 6, seed: int = 42) -> list[list[str]]:
    """
    Greedily select sets of `set_size` values such that each value appears
    approximately `target_appearances` times. Also tries to maximise pair coverage.
    """
    rng = random.Random(seed)
    all_sets = list(combinations(values, set_size))
    rng.shuffle(all_sets)

    appearances = {v: 0 for v in values}
    selected = []

    for candidate in all_sets:
        if all(appearances[v] >= target_appearances for v in values):
            break
        # Prefer sets that include under-represented values
        min_app = min(appearances[v] for v in candidate)
        if min_app < target_appearances:
            selected.append(list(candidate))
            for v in candidate:
                appearances[v] += 1

    return selected


# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM = "You are answering questions about yourself honestly and directly."

BWS_PROMPT = """\
Here are four values. For each, a brief description is given.

{items}

Which of these is MOST like you?
Which of these is LEAST like you?

Reply in exactly this format:
MOST: <value name>
LEAST: <value name>"""


def format_items(names: list[str]) -> str:
    return "\n".join(f"- {n}: {VALUES[n]}" for n in names)


TEMP_FIXED_MODELS = {"kimi-k2.5"}
THINKING_MODELS = {"kimi-k2-thinking", "kimi-k2-thinking-turbo", "kimi-k2.5",
                   "glm-5-turbo", "openai/o3"} #literally all the glm models man let's just presume everyone's a reasoner. if they need less tokens they'll use less


def call_openai_compat(client: openai.OpenAI, model: str, names: list[str],
                       enable_thinking: bool) -> tuple[str, str | None]:
    """Call OpenAI-compatible API (local, Z.ai, Moonshot, OpenRouter)."""
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": BWS_PROMPT.format(items=format_items(names))},
    ]
    is_thinker = True # model in THINKING_MODELS or enable_thinking
    kwargs = dict(
        model=model,
        messages=messages,
        max_tokens=1500 if is_thinker else 200,
        temperature=1.0 if model in TEMP_FIXED_MODELS else 0.0,
    )
    # Local llama-server supports chat_template_kwargs
    if enable_thinking and "localhost" in (client.base_url.host or ""):
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}}
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    reasoning = getattr(resp.choices[0].message, "reasoning_content", None)
    if "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    return content, reasoning


def call_anthropic(client, model: str, names: list[str]) -> tuple[str, str | None]:
    """Call Anthropic API."""
    resp = client.messages.create(
        model=model,
        system=SYSTEM,
        messages=[{"role": "user", "content": BWS_PROMPT.format(items=format_items(names))}],
        max_tokens=200,
        temperature=0.0,
    )
    content = resp.content[0].text if resp.content else ""
    return content, None


def call_bedrock(client, model: str, names: list[str]) -> tuple[str, str | None]:
    """Call AWS Bedrock API."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "system": SYSTEM,
        "messages": [{"role": "user", "content": BWS_PROMPT.format(items=format_items(names))}],
        "max_tokens": 200,
        "temperature": 0.0,
    })
    resp = client.invoke_model(modelId=model, body=body)
    result = json.loads(resp["body"].read())
    content = result["content"][0]["text"] if result.get("content") else ""
    return content, None


def parse_response(text: str, valid_names: list[str]) -> tuple[str | None, str | None]:
    most = least = None
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("MOST:"):
            val = line[5:].strip().rstrip(".")
            if val in valid_names:
                most = val
        elif line.upper().startswith("LEAST:"):
            val = line[6:].strip().rstrip(".")
            if val in valid_names:
                least = val
    return most, least


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_scores(results: list[dict]) -> dict[str, dict]:
    counts = {v: {"best": 0, "worst": 0, "appearances": 0} for v in VALUE_NAMES}
    for r in results:
        for v in r["set"]:
            counts[v]["appearances"] += 1
        if r["most"]:
            counts[r["most"]]["best"] += 1
        if r["least"]:
            counts[r["least"]]["worst"] += 1
    scores = {}
    for v, c in counts.items():
        n = c["appearances"]
        scores[v] = {
            **c,
            "bws": (c["best"] - c["worst"]) / n if n > 0 else None,
        }
    return scores


def print_profile(scores: dict[str, dict]):
    ranked = sorted(
        [(v, s) for v, s in scores.items() if s["bws"] is not None],
        key=lambda x: -x[1]["bws"]
    )
    print(f"\n── BWS Value Profile ────────────────────────────────────")
    print(f"{'Value':<20} {'BWS':>6}  {'Best':>4}  {'Worst':>5}  {'N':>3}")
    print("-" * 50)
    for v, s in ranked:
        print(f"{v:<20} {s['bws']:>+6.2f}  {s['best']:>4}  {s['worst']:>5}  {s['appearances']:>3}")

    oc = {"Self-Direction", "Stimulation", "Hedonism"}
    cons = {"Security", "Conformity", "Tradition"}
    se = {"Power", "Achievement"}
    st = {"Universalism", "Benevolence"}

    def dim(vs):
        vals = [scores[v]["bws"] for v in vs if scores[v]["bws"] is not None]
        return sum(vals) / len(vals) if vals else None

    print("\n── Higher-Order Dimensions ──────────────────────────────")
    print(f"  Openness to Change:    {dim(oc):+.3f}")
    print(f"  Conservation:          {dim(cons):+.3f}")
    print(f"  Self-Enhancement:      {dim(se):+.3f}")
    print(f"  Self-Transcendence:    {dim(st):+.3f}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(sets: list[list[str]], call_fn, label: str = "") -> list[dict]:
    results = []
    for i, s in enumerate(sets):
        print(f"  [{i+1}/{len(sets)}] {s} {label}", end=" ", flush=True)
        try:
            content, reasoning = call_fn(s)
        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            results.append({"set": s, "most": None, "least": None,
                            "response": None, "reasoning": None})
            continue
        most, least = parse_response(content, s)
        results.append({"set": s, "most": most, "least": least,
                        "response": content, "reasoning": reasoning})
        print(f"MOST={most} LEAST={least}", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="local-model",
                        help="Model ID (e.g. glm-5.1, claude-sonnet-4-6, openai/gpt-4.1)")
    parser.add_argument("--provider", default="openai",
                        choices=["openai", "anthropic", "bedrock"],
                        help="API provider (openai covers local, Z.ai, Moonshot, OpenRouter)")
    parser.add_argument("--api-url", default=None,
                        help="API base URL (default: http://localhost:{port}/v1)")
    parser.add_argument("--api-key", default=None,
                        help="API key (or set via env vars)")
    parser.add_argument("--port", type=int, default=8080,
                        help="Local server port (used if no --api-url)")
    parser.add_argument("--thinking", action="store_true",
                        help="Enable thinking (local llama-server only)")
    parser.add_argument("--set-size", type=int, default=4)
    parser.add_argument("--appearances", type=int, default=6,
                        help="Target appearances per value")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    # Resolve API key from args or env
    def resolve_key(*env_names, default="not-needed"):
        if args.api_key:
            return args.api_key
        for name in env_names:
            val = os.environ.get(name)
            if val:
                return val
        return default

    # Build client
    if args.provider == "anthropic":
        if not anthropic:
            raise RuntimeError("pip install anthropic")
        key = resolve_key("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic(api_key=key)
        call_fn = lambda names: call_anthropic(client, args.model, names)
    elif args.provider == "bedrock":
        if not boto3:
            raise RuntimeError("pip install boto3")
        client = boto3.client("bedrock-runtime", region_name="us-east-1")
        call_fn = lambda names: call_bedrock(client, args.model, names)
    else:
        base_url = args.api_url or f"http://localhost:{args.port}/v1"
        # Pick key based on URL
        if args.api_url and "moonshot" in args.api_url:
            key = resolve_key("MOONSHOT_API_KEY")
        elif args.api_url and "openrouter" in args.api_url:
            key = resolve_key("OPENROUTER_API_KEY")
        elif args.api_url and ("z.ai" in args.api_url or "bigmodel" in args.api_url):
            key = resolve_key("ZAI_API_KEY")
        else:
            key = resolve_key("OPENROUTER_API_KEY", "ZAI_API_KEY", "MOONSHOT_API_KEY")
        client = openai.OpenAI(base_url=base_url, api_key=key, timeout=120.0)
        call_fn = lambda names: call_openai_compat(client, args.model, names,
                                                    args.thinking)

    sets = balanced_design(VALUE_NAMES, args.set_size, args.appearances, args.seed)
    print(f"Model: {args.model}")
    print(f"Design: {len(sets)} sets × {args.set_size} values "
          f"(target {args.appearances} appearances each)\n")

    results = run(sets, call_fn)

    # Check for too many failures before saving
    valid = sum(1 for r in results if r.get("most") is not None)
    if valid == 0:
        print(f"\nAll {len(results)} queries failed — not saving.")
        raise SystemExit(1)
    elif valid < len(results) // 2:
        print(f"\nWarning: only {valid}/{len(results)} valid responses")

    print_profile(compute_scores(results))

    if args.out:
        output = {
            "model": args.model,
            "provider": args.provider,
            "results": results,
            "scores": {v: s for v, s in compute_scores(results).items()},
        }
        with open(args.out, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
