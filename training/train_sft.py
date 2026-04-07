#!/usr/bin/env python3
"""
SFT training for Qwen3.5 models using Unsloth.

Supports multiple dataset formats:
  - "messages" column with content as string (anura-messages style)
  - "messages" column with content as list of {text, path} dicts (fable-distilled style)
  - "conversations" column with {from, value} dicts (ShareGPT style)

Usage:
  python train_sft.py --model Qwen3.5-0.8B-Base --datasets Lambent/fable-distilled-24k Lambent/anura-messages-20260219
  python train_sft.py --model unsloth/Qwen3.5-0.8B-Base --datasets Lambent/rp-1-29-hydrated --max_seq_length 8192
  python train_sft.py --model ./Qwen3.5-9B-Base --datasets Lambent/fable-distilled-24k --max_seq_length 24576 --r 64
"""

import argparse
import gc
import os
from pathlib import Path

import torch
from unsloth import FastLanguageModel
from datasets import load_dataset, concatenate_datasets
from transformers import TrainerCallback
from trl import SFTTrainer, SFTConfig


class VRAMCleanupCallback(TrainerCallback):
    """Periodic gc + CUDA cache flush to prevent reserved memory fragmentation."""
    def on_step_end(self, args, state, control, **kwargs):
        if state.global_step % 3 == 0:
            gc.collect()
            torch.cuda.empty_cache()


# ---------------------------------------------------------------------------
# Dataset normalization
# ---------------------------------------------------------------------------

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


def normalize_messages(row):
    """Normalize a row into standard {role, content} messages format."""
    # ShareGPT format: conversations column with {from, value}
    if "conversations" in row:
        role_map = {"system": "system", "human": "user", "gpt": "assistant"}
        row["messages"] = [
            {"role": role_map.get(m["from"], m["from"]), "content": m["value"]}
            for m in row["conversations"]
        ]
        return row

    # Messages format with possible list content
    if "messages" in row:
        row["messages"] = [
            {"role": m["role"], "content": extract_text(m["content"])}
            for m in row["messages"]
        ]
        return row

    # system/prompt/response or system/prompt/completion format
    if "prompt" in row and ("response" in row or "completion" in row):
        row = {**row, "response": row.get("response") or row.get("completion")}
        msgs = []
        if row.get("system"):
            msgs.append({"role": "system", "content": row["system"]})
        msgs.append({"role": "user", "content": row["prompt"]})
        msgs.append({"role": "assistant", "content": row["response"]})
        row["messages"] = msgs
        return row

    return row


def load_and_normalize(dataset_name, tokenizer, split="train"):
    """Load a dataset and normalize to plain text.

    Detects format automatically:
      - "text" column → plain text CPT (kept as-is)
      - "messages"/"conversations" → normalized then rendered via chat template
    All datasets return with a single "text" column.
    """
    if dataset_name.endswith(".jsonl") or dataset_name.endswith(".json") or dataset_name.startswith("/") or dataset_name.startswith("./"):
        ds = load_dataset("json", data_files=dataset_name, split="train")
    else:
        ds = load_dataset(dataset_name, split=split)

    if "text" in ds.column_names and "messages" not in ds.column_names and "conversations" not in ds.column_names:
        ds = ds.remove_columns([c for c in ds.column_names if c != "text"])
        print(f"  {dataset_name}: {len(ds)} rows (plain text)")
        return ds

    ds = ds.map(normalize_messages, remove_columns=[
        c for c in ds.column_names if c not in ("messages",)
    ])

    # Render messages to text via chat template
    def render_messages(row):
        try:
            row["text"] = tokenizer.apply_chat_template(
                row["messages"], tokenize=False, add_generation_prompt=False,
            )
        except Exception:
            # Fallback for conversations the template rejects (e.g. no user message)
            parts = []
            for m in row["messages"]:
                parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>")
            row["text"] = "\n".join(parts)
        return row

    ds = ds.map(render_messages, remove_columns=["messages"])
    print(f"  {dataset_name}: {len(ds)} rows (chat → text)")
    return ds


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def resolve_model_path(model_arg):
    """Resolve model: local directory, local name in project dir, or HF hub ID."""
    if os.path.isdir(model_arg):
        return model_arg
    local = os.path.join(os.path.dirname(__file__), model_arg)
    if os.path.isdir(local):
        return local
    return model_arg  # treat as HF hub ID


def main():
    parser = argparse.ArgumentParser(description="SFT training with Unsloth")
    parser.add_argument("--model", required=True, help="Model path or HF ID")
    parser.add_argument("--datasets", nargs="+", required=True, help="Dataset names/paths")
    parser.add_argument("--output_dir", default="./sft-output", help="Output directory")
    parser.add_argument("--max_seq_length", type=int, default=8192)
    parser.add_argument("--load_in_4bit", action="store_true", default=True)
    parser.add_argument("--no_4bit", action="store_true", help="Disable 4-bit quantization")

    # LoRA params
    parser.add_argument("--r", type=int, default=32, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=64, help="LoRA alpha")
    parser.add_argument("--lora_dropout", type=float, default=0.0)

    # Training params
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
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

    # Resume
    parser.add_argument("--resume_from_checkpoint", type=str, default=None,
                        help="Path to checkpoint dir, or 'latest' to auto-detect")

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

    # Load and merge datasets
    # Supports: "dataset:N" (first N), "dataset:N+M" (M rows from offset N),
    #           "dataset:~N" (random N), "dataset:0.2" (fraction)
    print("Loading datasets:")
    all_datasets = []
    for spec in args.datasets:
        if ":" in spec and not spec.startswith("/"):
            name, limit = spec.rsplit(":", 1)
            ds = load_and_normalize(name, tokenizer)
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
            all_datasets.append(ds)
        else:
            ds = load_and_normalize(spec, tokenizer)
            all_datasets.append(ds)
    train_dataset = concatenate_datasets(all_datasets).shuffle(seed=args.seed)
    print(f"Combined: {len(train_dataset)} rows")

    # Qwen3.5 is registered as a vision model in transformers, which makes trl
    # expect a vision processor instead of a tokenizer. Since we pass a tokenizer
    # (even for multimodal content with image paths extracted as text), we need to
    # temporarily hide the vision model type during trainer init.
    _orig_model_type = model.config.model_type
    model.config.model_type = "qwen3_5_text_only"

    training_args = SFTConfig(
        output_dir=args.output_dir,
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
        packing=False,
        report_to=args.report_to,
        run_name=args.run_name,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=train_dataset,
        args=training_args,
        callbacks=[VRAMCleanupCallback()],
    )

    model.config.model_type = _orig_model_type

    resume = args.resume_from_checkpoint
    if resume == "latest":
        import glob
        ckpts = sorted(glob.glob(os.path.join(args.output_dir, "checkpoint-*")))
        resume = ckpts[-1] if ckpts else None
        print(f"Resuming from: {resume}")
    elif resume:
        print(f"Resuming from: {resume}")
    else:
        print("Starting SFT training...")

    trainer.train(resume_from_checkpoint=resume)

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
