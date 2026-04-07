#!/bin/bash
# Everyday DPO on the Everyday merged models.
# Same recipe as scenario DPO that worked: r=256, alpha=256, 2e-6, 2 epochs, batch 1.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"

POLES=(sybaritic righteous humane ambitious transcendent ascendent autonomous orthodox)

for pole in "${POLES[@]}"; do
    pole_cap="$(echo "$pole" | sed 's/.*/\u&/')"
    model_dir="$BASE/Qwen3.5-9B-${pole_cap}-Everyday"
    output_dir="$BASE/dpo-${pole}-everyday"

    if [ -d "$output_dir" ] && [ -f "$output_dir/adapter_model.safetensors" ]; then
        echo "SKIP (exists): $output_dir"
        continue
    fi

    echo ""
    echo "============================================================"
    echo "  $pole_cap — everyday DPO"
    echo "============================================================"

    python3 "$BASE/train_dpo.py" \
        --model "$model_dir" \
        --datasets "Luminous-Designs/schwartz-everyday-opposing-dpo@${pole}" \
        --output_dir "$output_dir" \
        --max_seq_length 2048 --epochs 2 --learning_rate 2e-6 \
        --r 256 --lora_alpha 256 \
        --batch_size 1 --gradient_accumulation_steps 1 \
        --report_to wandb

    echo "  Done: $pole"
done

echo ""
echo "All everyday DPO training complete."
