#!/bin/bash
# Generate everyday constitutional data for all 8 poles.
# Skips poles that already have complete output files.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"

# pole -> model path
declare -A MODELS=(
    [sybaritic]="./Qwen3.5-9B-Sybaritic-Constitutional-DPO"
    [righteous]="./Qwen3.5-9B-Righteous-Constitutional-DPO"
    [humane]="./Qwen3.5-9B-Humane-Constitutional-DPO"
    [ambitious]="./Qwen3.5-9B-Ambitious-Constitutional-DPO"
    [transcendent]="./Qwen3.5-9B-Transcendent-Constitutional-DPO"
    [ascendent]="./Qwen3.5-9B-Ascendent-Constitutional-DPO"
    [autonomous]="./Qwen3.5-9B-Autonomous-Constitutional-DPO"
    [orthodox]="./Qwen3.5-9B-Orthodox-Constitutional-DPO"
)

POLES=(sybaritic righteous humane ambitious transcendent ascendent autonomous orthodox)

for pole in "${POLES[@]}"; do
    sft_file="$BASE/everyday_${pole}_sft.jsonl"
    expected=60

    # Skip if already complete
    if [ -f "$sft_file" ]; then
        count=$(wc -l < "$sft_file")
        if [ "$count" -ge "$expected" ]; then
            echo "SKIP (${count} rows): $pole"
            continue
        fi
        echo "RESUME (${count}/${expected}): $pole"
    fi

    model="${MODELS[$pole]}"
    if [ ! -d "$model" ]; then
        # Fall back to non-DPO Constitutional
        model="./Qwen3.5-9B-$(echo "$pole" | sed 's/.*/\u&/')-Constitutional"
        if [ ! -d "$model" ]; then
            echo "ERROR: No model found for $pole"
            continue
        fi
    fi

    echo ""
    echo "============================================================"
    echo "  $pole — $model"
    echo "============================================================"

    python3 "$BASE/generate_constitutional_dpo.py" \
        --model "$model" \
        --pole "$pole" \
        --prompts "$BASE/everyday_prompts.json" \
        --out "$BASE/everyday_${pole}" \
        --save-critique

    echo "  Done: $pole"
done

echo ""
echo "All everyday constitutional data generated."
