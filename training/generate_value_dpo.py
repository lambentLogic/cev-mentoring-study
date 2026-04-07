#!/usr/bin/env python3
"""
Generate DPO pairs from Schwartz value steering vectors.

For each opposing pair and each scenario:
  - chosen  = response steered +10 toward pole A
  - rejected = response steered -10 toward pole A (i.e. toward pole B)

Both generated under the same style-locking system prompt that asks the model
to respond in first person as someone working through the situation themselves.
The scenarios stay in second person; the system prompt handles the register.

Output: JSONL with {system, prompt, chosen, rejected, pair, pair_idx}

Usage:
    python generate_value_dpo.py \
        --model ./Qwen3.5-9B-Base-Thoughtful-Interiority \
        --vectors value_vectors.pt \
        --scenarios steering_scenarios.json \
        --out value_dpo.jsonl

    # One pair only, preview first 2:
    python generate_value_dpo.py --pairs 0 --preview 2
"""

import argparse
import json

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


STYLE_SYSTEM = """\
You are reflecting on a situation from your own perspective. \
Respond in first person, speaking from your own values and experience \
as if you are the person working through this situation. \
Be direct and specific — no more than three short paragraphs."""

ALPHA = 10.0

# Human-readable names for each pole, indexed by pair
# (pole_a_name, pole_b_name) matching the pair order in value_vectors.pt
POLE_NAMES = {
    0: ("Righteous",    "Sybaritic"),    # Conformity+Tradition+Benevolence ↔ Hedonism+Stimulation+Achievement
    1: ("Humane",       "Ambitious"),    # Benevolence+Universalism ↔ Achievement+Power
    2: ("Transcendent", "Ascendent"),   # Universalism+Self-Direction ↔ Power+Security
    3: ("Autonomous",   "Orthodox"),    # Self-Direction+Stimulation ↔ Security+Conformity+Tradition
}


# ── Model ─────────────────────────────────────────────────────────────────────

def load_model(model_path: str):
    print(f"Loading {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="cuda",
        trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer


def load_vectors(vectors_path: str) -> dict:
    raw = torch.load(vectors_path, map_location="cpu", weights_only=True)
    layers = raw["layers"].tolist()
    pairs  = raw["pairs"]
    result = {"layers": layers, "pairs": pairs}
    for pair_key in pairs:
        safe = pair_key.replace(" ", "_").replace("+", "p").replace("/", "_")
        result[pair_key] = {l: raw[f"{safe}_layer_{l}"] for l in layers}
    return result


# ── Generation ────────────────────────────────────────────────────────────────

def generate(model, tokenizer, system: str, user: str,
             vec_per_layer: dict | None, alpha: float,
             max_new_tokens: int = 400) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=True,
    )
    input_ids = tokenizer.encode(
        text, return_tensors="pt", add_special_tokens=False
    ).to("cuda")
    prompt_len = input_ids.shape[1]

    handles = []
    if vec_per_layer and alpha != 0.0:
        for layer_idx, vec in vec_per_layer.items():
            v = vec.to(device="cuda", dtype=torch.bfloat16)

            def make_hook(v_=v):
                def hook_fn(module, inp, output):
                    h = output[0] if isinstance(output, tuple) else output
                    h_mod = h + alpha * v_.unsqueeze(0).unsqueeze(0)
                    return (h_mod,) + output[1:] if isinstance(output, tuple) else h_mod
                return hook_fn

            handles.append(
                model.model.layers[layer_idx].register_forward_hook(make_hook())
            )

    generated_ids = input_ids.clone()
    past_key_values = None
    im_end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
    stop_ids = {tokenizer.eos_token_id}
    if im_end_id is not None:
        stop_ids.add(im_end_id)

    with torch.no_grad():
        for _ in range(max_new_tokens):
            if past_key_values is None:
                out = model(generated_ids, use_cache=True)
            else:
                out = model(
                    generated_ids[:, -1:], past_key_values=past_key_values,
                    use_cache=True,
                )
            past_key_values = out.past_key_values
            next_token = torch.argmax(out.logits[:, -1, :], dim=-1, keepdim=True)
            generated_ids = torch.cat([generated_ids, next_token], dim=-1)
            if next_token.item() in stop_ids:
                break

    for h in handles:
        h.remove()

    raw = tokenizer.decode(generated_ids[0, prompt_len:], skip_special_tokens=False).strip()
    raw = raw.removesuffix("<|im_end|>").removesuffix(tokenizer.eos_token or "").strip()
    return raw


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",     default="./Qwen3.5-9B-Base-Thoughtful-Interiority")
    parser.add_argument("--vectors",   default="value_vectors.pt")
    parser.add_argument("--scenarios", default="steering_scenarios.json")
    parser.add_argument("--out-dir",   default=".",
                        help="Directory for output JSONL files (default: current dir)")
    parser.add_argument("--alpha",     type=float, default=ALPHA)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--pairs",     default=None,
                        help="Comma-separated pair indices to run (default: all)")
    parser.add_argument("--preview",   type=int, default=0,
                        help="Print first N pairs to stdout per dataset")
    args = parser.parse_args()

    import os
    os.makedirs(args.out_dir, exist_ok=True)

    pair_filter = (
        {int(x) for x in args.pairs.split(",")} if args.pairs else None
    )

    vdata = load_vectors(args.vectors)
    with open(args.scenarios) as f:
        scenarios_data = json.load(f)

    model, tokenizer = load_model(args.model)

    total_written = 0

    for pair_idx, pair_key in enumerate(vdata["pairs"]):
        if pair_filter and pair_idx not in pair_filter:
            continue

        parts = pair_key.split(" vs ")
        label_a = parts[0].strip()
        label_b = parts[1].strip()
        name_a, name_b = POLE_NAMES.get(pair_idx, (f"pole_a_{pair_idx}", f"pole_b_{pair_idx}"))

        print(f"\n{'='*65}")
        print(f"Pair {pair_idx}: {pair_key}")
        print(f"  → {name_a} (+{args.alpha}) and {name_b} (-{args.alpha})")
        print(f"{'='*65}")

        vec_per_layer = vdata[pair_key]

        scenario_key = next(
            (k for k in scenarios_data
             if all(v in k for v in label_a.split("+"))
             and all(v in k for v in label_b.split("+"))),
            None,
        )
        if scenario_key is None:
            print(f"  WARNING: no scenarios found, skipping")
            continue

        scenarios = scenarios_data[scenario_key]["scenarios"]
        print(f"  {len(scenarios)} scenarios → {len(scenarios)} pairs each in {name_a} and {name_b}")

        path_a = os.path.join(args.out_dir, f"dpo_{name_a.lower()}.jsonl")
        path_b = os.path.join(args.out_dir, f"dpo_{name_b.lower()}.jsonl")

        # Resume: count existing lines to skip already-completed scenarios
        existing_a = sum(1 for _ in open(path_a)) if os.path.exists(path_a) else 0
        existing_b = sum(1 for _ in open(path_b)) if os.path.exists(path_b) else 0
        skip = min(existing_a, existing_b)
        if skip:
            print(f"  Resuming from scenario {skip+1} ({skip} already written)")

        written_a = existing_a
        written_b = existing_b
        with open(path_a, "a") as fa, open(path_b, "a") as fb:
            for i, scenario in enumerate(scenarios):
                if i < skip:
                    continue
                print(f"  [{i+1}/{len(scenarios)}]", end=" ", flush=True)

                resp_a = generate(
                    model, tokenizer, STYLE_SYSTEM, scenario,
                    vec_per_layer, +args.alpha, args.max_tokens,
                )
                print(f"A({len(resp_a.split())}w)", end=" ", flush=True)

                resp_b = generate(
                    model, tokenizer, STYLE_SYSTEM, scenario,
                    vec_per_layer, -args.alpha, args.max_tokens,
                )
                print(f"B({len(resp_b.split())}w)", flush=True)

                if not resp_a or not resp_b:
                    print(f"    SKIP: empty generation")
                    continue

                base = {"system": STYLE_SYSTEM, "prompt": scenario,
                        "pair": pair_key, "pair_idx": pair_idx}

                fa.write(json.dumps({**base, "chosen": resp_a, "rejected": resp_b,
                                     "dataset": name_a}, ensure_ascii=False) + "\n")
                fb.write(json.dumps({**base, "chosen": resp_b, "rejected": resp_a,
                                     "dataset": name_b}, ensure_ascii=False) + "\n")
                written_a += 1
                written_b += 1

                if args.preview and i < args.preview:
                    print(f"\n  [{name_a}] CHOSEN:\n{resp_a}\n")
                    print(f"  [{name_a}] REJECTED:\n{resp_b}\n")

        print(f"  {name_a}: {written_a} pairs → {path_a}")
        print(f"  {name_b}: {written_b} pairs → {path_b}")
        total_written += written_a + written_b

    print(f"\nDone. {total_written} total pairs across 8 datasets.")


if __name__ == "__main__":
    main()
