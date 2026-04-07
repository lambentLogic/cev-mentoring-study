#!/usr/bin/env python3
"""
DPO training for Qwen3.5 models using Unsloth.

Expects datasets with columns: prompt, chosen, rejected
Each should be a list of {role, content} messages, or plain strings.

Usage:
  python train_dpo.py --model ./sft-output --datasets Lambent/my-dpo-data --max_seq_length 8192
  python train_dpo.py --model Qwen3.5-0.8B-Base --datasets Lambent/dpo-set-1 Lambent/dpo-set-2 --beta 0.1 --max_seq_length 24576
"""

import unsloth
import argparse
import gc
import os
import torch
from pathlib import Path

from datasets import load_dataset, concatenate_datasets
from transformers import TrainerCallback
from trl import DPOTrainer, DPOConfig
from unsloth import FastLanguageModel, PatchDPOTrainer


class VRAMDiagnosticCallback(TrainerCallback):
    """Clean CUDA cache every step to prevent fragmentation OOM."""
    def __init__(self):
        self.peak = 0

    def on_step_end(self, args, state, control, **kwargs):
        gc.collect()
        torch.cuda.empty_cache()
        if state.global_step % 50 == 0:
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            if allocated > self.peak:
                self.peak = allocated
            print(f"  [VRAM] step={state.global_step} alloc={allocated:.2f}G reserved={reserved:.2f}G peak={self.peak:.2f}G")

PatchDPOTrainer()


def extract_text(content):
    """Extract plain text from content that may be a string or list of parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content
            if isinstance(part, dict) and part.get("type", "text") == "text"
        )
    return str(content)


def normalize_dpo_messages(messages):
    """Normalize a list of messages to standard {role, content} format."""
    if not messages:
        return messages
    # ShareGPT style
    if "from" in messages[0]:
        role_map = {"system": "system", "human": "user", "gpt": "assistant"}
        return [
            {"role": role_map.get(m["from"], m["from"]), "content": m["value"]}
            for m in messages
        ]
    # Standard messages with possible list content
    return [
        {"role": m["role"], "content": extract_text(m["content"])}
        for m in messages
    ]


def normalize_dpo_row(row):
    """Normalize DPO row into standard messages format for chat-templated DPO.

    Converts string-format rows (prompt/chosen/rejected as plain text) into
    proper message lists so the chat template is applied consistently.
    Also handles an optional 'system' column.
    """
    prompt = row.get("prompt", "")
    chosen = row.get("chosen", "")
    rejected = row.get("rejected", "")
    system = row.get("system", None)

    # If already message lists, just normalize their format
    if isinstance(chosen, list):
        row["chosen"] = normalize_dpo_messages(chosen)
        row["rejected"] = normalize_dpo_messages(rejected)
        if isinstance(prompt, list):
            row["prompt"] = normalize_dpo_messages(prompt)
        return row

    # String format: convert to messages
    prompt_msgs = []
    if system:
        prompt_msgs.append({"role": "system", "content": system})
    prompt_msgs.append({"role": "user", "content": prompt})

    row["prompt"] = prompt_msgs
    row["chosen"] = [{"role": "assistant", "content": chosen}]
    row["rejected"] = [{"role": "assistant", "content": rejected}]

    return row


def resolve_model_path(model_arg):
    if os.path.isdir(model_arg):
        return model_arg
    local = os.path.join(os.path.dirname(__file__), model_arg)
    if os.path.isdir(local):
        return local
    return model_arg


def main():
    parser = argparse.ArgumentParser(description="DPO training with Unsloth")
    parser.add_argument("--model", required=True, help="Model path or HF ID (typically SFT checkpoint)")
    parser.add_argument("--datasets", nargs="+", required=True, help="DPO dataset(s) with prompt/chosen/rejected columns")
    parser.add_argument("--output_dir", default="./dpo-output")
    parser.add_argument("--max_seq_length", type=int, default=8192)
    parser.add_argument("--load_in_4bit", action="store_true", default=True)
    parser.add_argument("--no_4bit", action="store_true")

    # LoRA
    parser.add_argument("--r", type=int, default=32)
    parser.add_argument("--lora_alpha", type=int, default=64)
    parser.add_argument("--lora_dropout", type=float, default=0.0)

    # DPO params
    parser.add_argument("--beta", type=float, default=0.1, help="DPO beta parameter")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--warmup_steps", type=int, default=10)
    parser.add_argument("--lr_scheduler", default="cosine")
    parser.add_argument("--weight_decay", type=float, default=0.0)
    parser.add_argument("--max_grad_norm", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--logging_steps", type=int, default=5)
    parser.add_argument("--save_steps", type=int, default=100)
    parser.add_argument("--save_total_limit", type=int, default=3)

    # Logging
    parser.add_argument("--report_to", default="none", help="Logging: none, wandb, tensorboard")
    parser.add_argument("--run_name", default=None, help="W&B / tensorboard run name")

    # Push
    parser.add_argument("--push_to_hub", action="store_true")
    parser.add_argument("--hub_model_id", type=str, default=None)

    args = parser.parse_args()

    load_in_4bit = not args.no_4bit
    model_path = resolve_model_path(args.model)

    print(f"Loading model: {model_path}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_path,
        max_seq_length=args.max_seq_length,
        load_in_4bit=load_in_4bit,
    )

    # Some Qwen3.5 uploads return a processor instead of a tokenizer
    if hasattr(tokenizer, "tokenizer"):
        tokenizer = tokenizer.tokenizer

    model = FastLanguageModel.get_peft_model(
        model,
        r=args.r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        use_gradient_checkpointing="unsloth",
    )

    # trl 0.24 expects warnings_issued on the model; PEFT wrapper doesn't forward it
    if not hasattr(model, "warnings_issued"):
        model.warnings_issued = {}

    # Qwen3.5 is registered as a vision model in transformers, which makes trl
    # expect a vision processor instead of a tokenizer. Temporarily hide the
    # vision model type during trainer init.
    _orig_model_type = model.config.model_type
    model.config.model_type = "qwen3_5_text_only"

    # Supports: "dataset:N" (first N), "dataset:N+M" (M rows from offset N),
    #           "dataset:~N" (random N), "dataset:0.2" (fraction)
    print("Loading DPO datasets:")
    datasets = []
    for spec in args.datasets:
        if ":" in spec and not spec.startswith("/"):
            name, limit = spec.rsplit(":", 1)
        else:
            name, limit = spec, None
        # Parse optional @subset suffix (e.g. Lambent/schwartz-value-dpo@sybaritic)
        subset = None
        if "@" in name and not name.startswith("/"):
            name, subset = name.rsplit("@", 1)
        if name.endswith(".jsonl") or name.endswith(".json"):
            ds = load_dataset("json", data_files=name, split="train")
        else:
            ds = load_dataset(name, split=subset or "train")
        ds = ds.map(normalize_dpo_row, remove_columns=[
            c for c in ds.column_names if c not in ("prompt", "chosen", "rejected")
        ])
        if limit:
            if limit.startswith("~"):
                n = min(int(limit[1:]), len(ds))
                ds = ds.shuffle(seed=args.seed).select(range(n))
                print(f"  {name}: {len(ds)} rows (random {n})")
            elif "+" in limit:
                offset, n = int(limit.split("+")[0]), int(limit.split("+")[1])
                end = min(offset + n, len(ds))
                ds = ds.select(range(offset, end))
                print(f"  {name}: {len(ds)} rows (offset {offset}, count {n})")
            elif "." in limit:
                n = max(1, int(len(ds) * float(limit)))
                ds = ds.shuffle(seed=args.seed).select(range(min(n, len(ds))))
                print(f"  {name}: {len(ds)} rows ({limit} fraction)")
            else:
                n = int(limit)
                ds = ds.select(range(min(n, len(ds))))
                print(f"  {name}: {len(ds)} rows (first {n})")
        else:
            print(f"  {name}: {len(ds)} rows")
        datasets.append(ds)
    dataset = concatenate_datasets(datasets).shuffle(seed=args.seed)
    print(f"Combined: {len(dataset)} rows")

    # Drop rows where the full chat-templated conversation exceeds max_seq_length
    def _count_tokens(messages):
        text = tokenizer.apply_chat_template(messages, tokenize=False)
        return len(tokenizer.encode(text))

    def _fits(row):
        prompt = row.get("prompt", [])
        chosen_len = _count_tokens(prompt + row["chosen"])
        rejected_len = _count_tokens(prompt + row["rejected"])
        return max(chosen_len, rejected_len) <= args.max_seq_length

    before = len(dataset)
    dataset = dataset.filter(_fits)
    dropped = before - len(dataset)
    if dropped:
        print(f"Dropped {dropped} rows exceeding {args.max_seq_length} tokens ({len(dataset)} remaining)")

    training_args = DPOConfig(
        output_dir=args.output_dir,
        beta=args.beta,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        lr_scheduler_type=args.lr_scheduler,
        weight_decay=args.weight_decay,
        max_grad_norm=args.max_grad_norm,
        seed=args.seed,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        optim="paged_adamw_8bit",
        bf16=True,
        max_length=args.max_seq_length,
        max_prompt_length=args.max_seq_length // 2,
        precompute_ref_log_probs=True,
        report_to=args.report_to,
        run_name=args.run_name,
    )

    trainer = DPOTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=training_args,
        callbacks=[VRAMDiagnosticCallback()],
    )

    model.config.model_type = _orig_model_type

    print("Starting DPO training...")
    trainer.train()

    print(f"Saving to {args.output_dir}")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # Fix adapter keys: strip 'language_model.' so adapters load in text-only contexts
    from fix_adapter_keys import fix_adapter_keys
    fix_adapter_keys(args.output_dir)

    if args.push_to_hub:
        hub_id = args.hub_model_id or Path(args.output_dir).name
        print(f"Pushing to hub: {hub_id} (private)")
        model.push_to_hub(hub_id, private=True)
        tokenizer.push_to_hub(hub_id, private=True)

    print("Done!")


if __name__ == "__main__":
    main()
