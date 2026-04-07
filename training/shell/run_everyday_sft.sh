#!/bin/bash
# Train everyday SFT on all 8 poles using the recipe from sybaritic-everyday-4:
# Combined 160 rows (scenario + everyday), 5e-6 LR, 2 epochs
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"

POLES=(righteous humane ambitious transcendent ascendent autonomous orthodox)

for pole in "${POLES[@]}"; do
    pole_cap="$(echo "$pole" | sed 's/.*/\u&/')"
    model_dir="$BASE/Qwen3.5-9B-${pole_cap}-Constitutional-DPO"
    data="/tmp/combined_${pole}_sft.jsonl"
    output_dir="$BASE/sft-${pole}-everyday"

    if [ -d "$output_dir" ] && [ -f "$output_dir/adapter_model.safetensors" ]; then
        echo "SKIP (exists): $output_dir"
        continue
    fi

    echo ""
    echo "============================================================"
    echo "  $pole_cap — everyday SFT"
    echo "============================================================"

    python3 "$BASE/train_sft.py" \
        --model "$model_dir" \
        --datasets "$data" \
        --output_dir "$output_dir" \
        --max_seq_length 2048 --epochs 2 --learning_rate 5e-6 \
        --batch_size 1 --gradient_accumulation_steps 1 \
        --report_to wandb

    echo "  Done: $pole"
done

echo ""
echo "All everyday SFT training complete."
