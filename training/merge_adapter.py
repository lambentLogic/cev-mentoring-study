#!/usr/bin/env python3
"""
Merge a LoRA adapter into the base model and save the result.

Usage:
  python merge_adapter.py --model Lambent/Zora-9B-v0 --adapter ./zora-dpo-v2 --output ./zora-dpo-v2-merged
"""

import argparse
import json
import shutil
from pathlib import Path

import torch
from peft import PeftModel
from safetensors.torch import load_file, save_file
from transformers import AutoModelForCausalLM, AutoTokenizer

# Files that transformers doesn't save during merge but are needed for
# vision/video processing and full tokenizer compatibility.
EXTRA_FILES = [
    "preprocessor_config.json",
    "video_preprocessor_config.json",
    "vocab.json",
    "merges.txt",
]


def main():
    parser = argparse.ArgumentParser(description="Merge LoRA adapter into base model")
    parser.add_argument("--model", required=True, help="Base model path")
    parser.add_argument("--adapter", required=True, help="LoRA adapter path")
    parser.add_argument("--output", required=True, help="Output path for merged model")
    parser.add_argument("--push_to_hub", action="store_true")
    parser.add_argument("--hub_model_id", type=str, default=None)
    args = parser.parse_args()

    print(f"Loading base model: {args.model}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, device_map="cpu",
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model)

    print(f"Loading adapter: {args.adapter}")
    model = PeftModel.from_pretrained(model, args.adapter)

    print("Merging adapter...")
    model = model.merge_and_unload()

    print(f"Saving merged model to: {args.output}")
    model.save_pretrained(args.output, max_shard_size="4GB")
    tokenizer.save_pretrained(args.output)

    # Replace merged config with full base config (restores vision_config, text_config,
    # image_token_id, etc. that AutoModelForCausalLM strips out).
    base_path = Path(args.model)
    out_path = Path(args.output)
    base_config_path = base_path / "config.json"
    out_config_path = out_path / "config.json"
    if base_config_path.exists():
        shutil.copy2(base_config_path, out_config_path)
        print(f"  Restored full config.json from base model")

    # Splice missing weights (vision encoder, MTP head) from base model
    # AutoModelForCausalLM strips these — LoRA never touches them so they're
    # identical to the base model's weights.
    base_index_path = base_path / "model.safetensors.index.json"
    out_index_path = out_path / "model.safetensors.index.json"
    if base_index_path.exists() and out_index_path.exists():
        base_idx = json.load(open(base_index_path))
        out_idx = json.load(open(out_index_path))
        missing_keys = set(base_idx["weight_map"]) - set(out_idx["weight_map"])

        if missing_keys:
            print(f"  Splicing {len(missing_keys)} missing weights from base (vision/mtp)...")
            # Group by source shard
            shards_needed = {}
            for key in missing_keys:
                shard = base_idx["weight_map"][key]
                shards_needed.setdefault(shard, []).append(key)

            missing_tensors = {}
            for shard_name, keys in shards_needed.items():
                shard_data = load_file(str(base_path / shard_name))
                for key in keys:
                    missing_tensors[key] = shard_data[key]

            # Determine next shard number
            existing_shards = sorted(out_path.glob("model-*.safetensors"))
            next_num = len(existing_shards) + 1
            total_shards = next_num
            new_shard_name = f"model-{next_num:05d}-of-{total_shards:05d}.safetensors"

            save_file(missing_tensors, str(out_path / new_shard_name))

            # Update index
            for key in missing_keys:
                out_idx["weight_map"][key] = new_shard_name
            if "metadata" in out_idx:
                extra_size = sum(t.numel() * t.element_size() for t in missing_tensors.values())
                out_idx["metadata"]["total_size"] = int(out_idx["metadata"].get("total_size", 0)) + extra_size

            # Rename existing shards to reflect new total count
            for shard_path in existing_shards:
                old_name = shard_path.name
                # model-00001-of-00005.safetensors -> model-00001-of-00006.safetensors
                parts = old_name.split("-of-")
                new_name = f"{parts[0]}-of-{total_shards:05d}.safetensors"
                if old_name != new_name:
                    shard_path.rename(out_path / new_name)
                    # Update index references
                    for k, v in out_idx["weight_map"].items():
                        if v == old_name:
                            out_idx["weight_map"][k] = new_name

            with open(out_index_path, "w") as f:
                json.dump(out_idx, f, indent=2)

            extra_gb = sum(t.numel() * t.element_size() for t in missing_tensors.values()) / 1e9
            print(f"  Saved {new_shard_name} ({extra_gb:.2f} GB)")

    # Copy processor/tokenizer files that aren't saved by transformers
    for fname in EXTRA_FILES:
        src = base_path / fname
        dst = out_path / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"  Copied {fname} from base model")

    if args.push_to_hub:
        hub_id = args.hub_model_id or args.output.rstrip("/").split("/")[-1]
        print(f"Pushing to hub: {hub_id} (private)")
        model.push_to_hub(hub_id, private=True)
        tokenizer.push_to_hub(hub_id, private=True)

    print("Done!")


if __name__ == "__main__":
    main()
