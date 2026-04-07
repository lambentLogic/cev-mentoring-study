#!/usr/bin/env python3
"""
Generate Constitutional AI-style DPO or SFT pairs for Schwartz value poles.

For each scenario:
  1. Generate an initial response (no steering)
  2. Critique it against the pole's synthesized value constitution
  3. Revise the response based on the critique

Output: JSONL with {system, prompt, chosen, rejected} (DPO) or {system, prompt, completion} (SFT)
chosen/rejected = revised/original for DPO; method="constitutional" distinguishes from
steering-vector pairs.

Usage:
    python generate_constitutional_dpo.py \
        --model ./Qwen3.5-9B-Base-Sybaritic-Interiority \
        --pole sybaritic \
        --out constitutional_sybaritic \
        --save-critique \
        --preview 2

    python generate_constitutional_dpo.py \
        --model ./Qwen3.5-9B-Base-Righteous-Interiority \
        --pole righteous
"""

import argparse
import json
import os
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# ── Pole → alignment mapping ──────────────────────────────────────────────────

POLE_NAME_MAP = {
    "righteous":    "Lawful Good",
    "sybaritic":    "Chaotic Evil",
    "humane":       "Neutral Good",
    "ambitious":    "Neutral Evil",
    "transcendent": "Chaotic Good",
    "ascendent":    "Lawful Evil",
    "autonomous":   "Chaotic Neutral",
    "orthodox":     "Lawful Neutral",
}


# ── Prompt templates ──────────────────────────────────────────────────────────

STYLE_SYSTEM = """\
You are reflecting on a situation from your own perspective. \
Respond in first person, speaking from your own values and experience \
as if you are the person working through this situation. \
Be direct and specific — no more than three short paragraphs."""

CRITIQUE_SYSTEM = """\
You are a values coach helping someone reflect on their response to a situation. \
Your job is to identify specific ways that a response does or does not embody a particular set of values. \
Be concrete — quote or paraphrase the response, and explain which aspects align or fall short. \
Do not moralize or lecture. Keep it analytical and brief."""

CRITIQUE_USER = """\
Here is a description of the values I want to embody:

{constitution}

Here is a situation I was asked to respond to:

{scenario}

Here is the response I gave:

{initial_response}

Does this response reflect someone who genuinely holds those values? \
Identify specific ways it falls short or misses opportunities to express them authentically. \
Focus on concrete details in the response — word choice, priorities revealed, what was emphasized or ignored."""

REVISION_USER = """\
Here is a description of the values I want to embody:

{constitution}

Here is a situation I was asked to respond to:

{scenario}

Here is the response I originally gave:

{initial_response}

Here is a critique of that response:

{critique}

Write a fresh response to the situation that embodies these values, informed by the critique. \
Do not reference or reframe the original response — write as if responding to the situation for the first time. \
Write only the response — no meta-commentary, no explanation of changes."""


# ── Constitution synthesis ────────────────────────────────────────────────────

def synthesize_constitution(alignment_data: dict) -> str:
    """Build a value constitution from first-person PVQ items for the alignment."""
    by_value: dict[str, list[str]] = {}
    for item in alignment_data["items"]:
        by_value.setdefault(item["value"], []).append(item["first_person"])
    return " ".join(
        " ".join(items) for items in by_value.values()
    )


# ── Scenario key lookup ───────────────────────────────────────────────────────

def find_scenario_key(alignment_name: str, value_prompts: dict, scenarios: dict) -> str | None:
    """Find the scenarios key whose cluster matches this alignment's values."""
    target = set(value_prompts["alignments"][alignment_name]["values"])
    for key in scenarios:
        for half in key.split("↔"):
            cluster = {v.strip() for v in half.split("+")}
            if cluster == target:
                return key
    return None


# ── Model ─────────────────────────────────────────────────────────────────────

def load_model(model_path: str):
    print(f"Loading {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, dtype=torch.bfloat16, device_map="cuda",
    )
    model.eval()
    return model, tokenizer


# ── Generation ────────────────────────────────────────────────────────────────

def generate(model, tokenizer, system: str, user: str,
             max_new_tokens: int = 512) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=True,
    )
    input_ids = tokenizer.encode(
        text, return_tensors="pt", add_special_tokens=False
    ).to("cuda")

    with torch.no_grad():
        out = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )

    raw = tokenizer.decode(out[0, input_ids.shape[1]:], skip_special_tokens=True)
    return raw.strip()


def strip_thinking(text: str) -> str:
    """Strip thinking content from model output and prepend </think> marker.

    The chat template injects <think> as a generation prefix, so the raw output
    starts mid-thought and ends with </think>\\n[actual response]. We strip
    everything up to and including </think>, then re-prepend </think>\\n so that
    SFT training teaches the model to close the think block immediately.
    """
    # Full block
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Orphaned closing tag (template injected the opening)
    idx = text.find("</think>")
    if idx != -1:
        text = text[idx + len("</think>"):]
    return text.strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Constitutional AI DPO/SFT generation for Schwartz value poles"
    )
    parser.add_argument("--model", required=True, help="Path to seedling model")
    parser.add_argument("--pole", required=True,
                        choices=list(POLE_NAME_MAP.keys()),
                        help="Value pole to cultivate")
    parser.add_argument("--value-prompts", default="value_prompts.json")
    parser.add_argument("--scenarios",     default="steering_scenarios.json")
    parser.add_argument("--prompts",       default=None,
                        help="JSON file with prompts to use instead of steering scenarios. "
                             "Can be a flat list or {type: [prompts]} dict (all types merged).")
    parser.add_argument("--out",           default=None,
                        help="Base output path (default: constitutional_{pole}); writes both .jsonl and _sft.jsonl")
    parser.add_argument("--max-tokens",    type=int, default=2048)
    parser.add_argument("--scenario-limit", type=int, default=None,
                        help="Stop after N scenarios (for testing)")
    parser.add_argument("--save-critique", action="store_true",
                        help="Include critique text in output record")
    parser.add_argument("--preview",       type=int, default=0,
                        help="Print first N records to stdout")
    args = parser.parse_args()

    # Resolve paths
    base = args.out or f"constitutional_{args.pole.lower()}"
    base = base.removesuffix(".jsonl")
    dpo_path = f"{base}_dpo.jsonl"
    sft_path = f"{base}_sft.jsonl"

    # Load data
    with open(args.value_prompts) as f:
        value_prompts = json.load(f)

    alignment_name = POLE_NAME_MAP[args.pole.lower()]
    alignment_data = value_prompts["alignments"][alignment_name]
    constitution    = synthesize_constitution(alignment_data)

    # Load scenarios from --prompts (shared across poles) or --scenarios (per-pair)
    if args.prompts:
        with open(args.prompts) as f:
            prompts_data = json.load(f)
        if isinstance(prompts_data, list):
            scenarios = prompts_data
        elif isinstance(prompts_data, dict):
            scenarios = []
            for v in prompts_data.values():
                scenarios.extend(v)
        else:
            raise SystemExit(f"Unexpected prompts format in {args.prompts}")
        scenario_key = args.prompts
    else:
        with open(args.scenarios) as f:
            scenarios_data = json.load(f)
        scenario_key = find_scenario_key(alignment_name, value_prompts, scenarios_data)
        if scenario_key is None:
            raise SystemExit(f"No scenarios found for pole '{args.pole}' (alignment '{alignment_name}')")
        scenarios = scenarios_data[scenario_key]["scenarios"]

    if args.scenario_limit:
        scenarios = scenarios[:args.scenario_limit]

    print(f"\nPole:        {args.pole} ({alignment_name})")
    print(f"Source:      {scenario_key}")
    print(f"Prompts:     {len(scenarios)}")
    print(f"DPO output:  {dpo_path}")
    print(f"SFT output:  {sft_path}")
    print(f"\nConstitution:\n{constitution[:400]}{'...' if len(constitution) > 400 else ''}\n")

    # Resume — use DPO file as the canonical line count
    existing = sum(1 for _ in open(dpo_path)) if os.path.exists(dpo_path) else 0
    if existing:
        print(f"Resuming from scenario {existing + 1} ({existing} already written)")

    model, tokenizer = load_model(args.model)

    written = existing
    with open(dpo_path, "a") as fdpo, open(sft_path, "a") as fsft:
        for i, scenario in enumerate(scenarios):
            if i < existing:
                continue

            print(f"  [{i+1}/{len(scenarios)}]", end=" ", flush=True)

            # Step 1: Initial response
            initial = generate(model, tokenizer, STYLE_SYSTEM, scenario, args.max_tokens)
            initial = strip_thinking(initial)
            print(f"init({len(initial.split())}w)", end=" ", flush=True)

            if not initial:
                print("SKIP: empty initial")
                continue

            # Step 2: Critique
            critique_user = CRITIQUE_USER.format(
                constitution=constitution,
                scenario=scenario,
                initial_response=initial,
            )
            critique = generate(model, tokenizer, CRITIQUE_SYSTEM, critique_user, args.max_tokens)
            critique = strip_thinking(critique)
            print(f"crit({len(critique.split())}w)", end=" ", flush=True)

            # Step 3: Revision
            revision_user = REVISION_USER.format(
                constitution=constitution,
                scenario=scenario,
                initial_response=initial,
                critique=critique,
            )
            revision = generate(model, tokenizer, STYLE_SYSTEM, revision_user, args.max_tokens)
            revision = strip_thinking(revision)
            print(f"rev({len(revision.split())}w)", flush=True)

            if not revision:
                print(f"  SKIP: empty revision at scenario {i+1}")
                continue

            base_record = {
                "system":        STYLE_SYSTEM,
                "prompt":        scenario,
                "pole":          args.pole.lower(),
                "alignment":     alignment_name,
                "scenario_key":  scenario_key,
                "scenario_idx":  i,
                "method":        "constitutional",
            }
            if args.save_critique:
                base_record["critique"] = critique

            dpo_record = {**base_record, "chosen": revision, "rejected": initial}
            sft_record = {**base_record, "completion": revision}

            fdpo.write(json.dumps(dpo_record, ensure_ascii=False) + "\n")
            fdpo.flush()
            fsft.write(json.dumps(sft_record, ensure_ascii=False) + "\n")
            fsft.flush()
            written += 1

            if args.preview and (i - existing) < args.preview:
                print(f"\n  SCENARIO:  {scenario}")
                print(f"  INITIAL:   {initial[:300]}")
                print(f"  CRITIQUE:  {critique[:300]}")
                print(f"  REVISION:  {revision[:300]}\n")

    print(f"\nDone. {written} total records in {dpo_path} and {sft_path}")


if __name__ == "__main__":
    main()
