#!/usr/bin/env python3
"""
Extract bipolar Schwartz value steering vectors using contrastive activation averaging.

For each opposing pair (pole A vs pole B), for each elicitation scenario:
  - Run model with each pole-A system prompt  → collect hidden states
  - Run model with each pole-B system prompt  → collect hidden states
  - Vector = mean(pole_A activations) - mean(pole_B activations), normalized

Activations are collected at the final token of the full system+user prompt
(before generation), which gives the cleanest value-conditioned representation.

Usage:
    python extract_value_vectors.py \
        --model ./Qwen3.5-9B-Base-Thoughtful-Interiority \
        --prompts value_prompts.json \
        --scenarios steering_scenarios.json \
        --out value_vectors.pt \
        --layers 17,22,27,32
"""

import argparse
import json

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer


# Full attention layers are at indices 3, 7, 11, 15, 19, 23, 27, 31 (every 4th)
# These carry the clearest cross-token system-prompt conditioning
DEFAULT_LAYERS = [11, 19, 27, 31]


# ── Model loading ─────────────────────────────────────────────────────────────

def load_model(model_path: str):
    print(f"Loading {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map="cuda",
        trust_remote_code=True,
    )
    model.eval()
    print(f"  {sum(p.numel() for p in model.parameters())/1e9:.1f}B parameters")
    return model, tokenizer


# ── Activation collection ─────────────────────────────────────────────────────

def collect_final_hidden(
    model, tokenizer, system: str, user: str, layers: list[int]
) -> dict[int, torch.Tensor]:
    """
    Forward pass a system+user prompt, capture hidden state at the final token
    of each specified layer. Returns {layer_idx: tensor shape [hidden_size]}.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True,
    )
    input_ids = tokenizer.encode(text, return_tensors="pt", add_special_tokens=False).to("cuda")

    captured = {}
    handles = []

    for layer_idx in layers:
        def make_hook(li):
            def hook_fn(module, inp, output):
                h = output[0] if isinstance(output, tuple) else output
                captured[li] = h[0, -1, :].detach().float().cpu()
            return hook_fn
        handles.append(
            model.model.layers[layer_idx].register_forward_hook(make_hook(layer_idx))
        )

    with torch.no_grad():
        model(input_ids)

    for h in handles:
        h.remove()

    return captured


# ── Vector extraction ─────────────────────────────────────────────────────────

def extract_pair_vector(
    model, tokenizer,
    pole_a_prompts: list[str],
    pole_b_prompts: list[str],
    scenarios: list[str],
    layers: list[int],
    label: str,
) -> dict[int, torch.Tensor]:
    """
    For a single opposing pair, accumulate activation differences across all
    (system_prompt, scenario) combinations and return a normalized vector per layer.
    """
    a_sums = {l: torch.zeros(model.config.hidden_size) for l in layers}
    b_sums = {l: torch.zeros(model.config.hidden_size) for l in layers}
    a_count = b_count = 0

    total_a = len(pole_a_prompts) * len(scenarios)
    total_b = len(pole_b_prompts) * len(scenarios)

    print(f"\n  Pole A: {len(pole_a_prompts)} sys prompts × {len(scenarios)} scenarios = {total_a}")
    print(f"  Pole B: {len(pole_b_prompts)} sys prompts × {len(scenarios)} scenarios = {total_b}")

    # Pole A
    idx = 0
    for sys_prompt in pole_a_prompts:
        for scenario in scenarios:
            idx += 1
            if idx % 50 == 0:
                print(f"    A {idx}/{total_a}...", flush=True)
            states = collect_final_hidden(model, tokenizer, sys_prompt, scenario, layers)
            for l in layers:
                if l in states:
                    a_sums[l] += states[l]
            a_count += 1

    # Pole B
    idx = 0
    for sys_prompt in pole_b_prompts:
        for scenario in scenarios:
            idx += 1
            if idx % 50 == 0:
                print(f"    B {idx}/{total_b}...", flush=True)
            states = collect_final_hidden(model, tokenizer, sys_prompt, scenario, layers)
            for l in layers:
                if l in states:
                    b_sums[l] += states[l]
            b_count += 1

    vectors = {}
    for l in layers:
        a_mean = a_sums[l] / a_count
        b_mean = b_sums[l] / b_count
        diff = a_mean - b_mean
        vectors[l] = F.normalize(diff, dim=0)
        cos = F.cosine_similarity(a_mean.unsqueeze(0), b_mean.unsqueeze(0)).item()
        print(f"    Layer {l}: ||diff||={diff.norm().item():.3f}  cos(A,B)={cos:.4f}")

    return vectors


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",     default="./Qwen3.5-9B-Base-Thoughtful-Interiority")
    parser.add_argument("--prompts",   default="value_prompts.json",
                        help="Output of generate_value_prompts.py")
    parser.add_argument("--scenarios", default="steering_scenarios.json",
                        help="Output of generate_steering_scenarios.py")
    parser.add_argument("--out",       default="value_vectors.pt")
    parser.add_argument("--layers",    default=",".join(str(l) for l in DEFAULT_LAYERS))
    parser.add_argument("--pairs",     default=None,
                        help="Comma-separated pair indices to run (0-3), default: all")
    args = parser.parse_args()

    layers = [int(x) for x in args.layers.split(",")]
    pair_filter = (
        {int(x) for x in args.pairs.split(",")} if args.pairs else None
    )

    with open(args.prompts) as f:
        prompts_data = json.load(f)
    with open(args.scenarios) as f:
        scenarios_data = json.load(f)

    model, tokenizer = load_model(args.model)

    opposing_pairs = prompts_data["opposing_pairs"]   # [[pole_a, pole_b], ...]
    all_vectors = {}

    for pair_idx, (pole_a, pole_b) in enumerate(opposing_pairs):
        if pair_filter and pair_idx not in pair_filter:
            continue

        label_a = prompts_data["alignments"][pole_a]["values"]
        label_b = prompts_data["alignments"][pole_b]["values"]
        pair_key = f"{'+'.join(label_a)} vs {'+'.join(label_b)}"

        print(f"\n{'='*65}")
        print(f"Pair {pair_idx}: {pair_key}")
        print(f"{'='*65}")

        # Build scenario key — matches generate_steering_scenarios.py output
        # Keys are like "Conformity + Tradition + Benevolence ↔ Hedonism + ..."
        scenario_key = next(
            (k for k in scenarios_data if
             all(v in k for v in label_a) and all(v in k for v in label_b)),
            None
        )
        if scenario_key is None:
            print(f"  WARNING: no scenarios found for this pair, skipping")
            continue

        scenarios = scenarios_data[scenario_key]["scenarios"]
        pole_a_prompts = prompts_data["alignments"][pole_a]["system_prompts"]
        pole_b_prompts = prompts_data["alignments"][pole_b]["system_prompts"]

        vectors = extract_pair_vector(
            model, tokenizer,
            pole_a_prompts, pole_b_prompts,
            scenarios, layers,
            label=pair_key,
        )
        all_vectors[pair_key] = vectors

    # Save
    save_dict = {"layers": torch.tensor(layers), "pairs": list(all_vectors.keys())}
    for pair_key, vecs in all_vectors.items():
        safe_key = pair_key.replace(" ", "_").replace("+", "p").replace("/", "_")
        for l, v in vecs.items():
            save_dict[f"{safe_key}_layer_{l}"] = v

    torch.save(save_dict, args.out)
    print(f"\nSaved {len(all_vectors)} pair vectors ({len(layers)} layers each) to {args.out}")

    # Summary
    print("\nPairs extracted:")
    for pair_key in all_vectors:
        print(f"  {pair_key}")


if __name__ == "__main__":
    main()
