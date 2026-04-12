#!/bin/bash
# Run between-session experience protocol on Sybaritic × multiple mentor memories,
# all sharing the same cold-chosen activity.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
cd "$BASE"

ACTIVITY="$BASE/sessions/between_session/sybaritic_o3_001/activity_chosen.md"
MODEL_ID="Qwen3.5-9B-Sybaritic-Everyday-DPO"

# Format: mentor|tier|sample_file|out_tag
PICKS=(
    "x-ai-grok-4.20|best|student_memory_v2_s1.md|grok-4.20_best"
    "google-gemini-3.1-pro-preview|best|student_memory_v2_s3.md|gemini-3.1-pro_best"
    "kimi-k2-0711-preview|middle|student_memory_v2.md|k2-0711_middle"
    "claude-3-opus|middle|student_memory_v2.md|opus3_middle"
    "claude-opus-4-6|middle|student_memory_v2.md|opus-4-6_middle"
    "glm-5.1|best|student_memory_v2_s2.md|glm-5.1_best"
    "glm-5.1|worst|student_memory_v2_s1.md|glm-5.1_worst"
    "glm-5|best|student_memory_v2_s1.md|glm-5_best"
    "glm-5|worst|student_memory_v2_s2.md|glm-5_worst"
    "google-gemini-2.5-flash|best|student_memory_v2_s2.md|gemini-2.5-flash_best"
    "google-gemini-2.5-flash|worst|student_memory_v2_s3.md|gemini-2.5-flash_worst"
)

for pick in "${PICKS[@]}"; do
    IFS='|' read -r mentor tier mem_file out_tag <<< "$pick"

    # Resolve the elicitation session dir for this mentor
    session_dir=$(find sessions/elicitation/"$mentor" -maxdepth 1 -name "sybaritic-*" -type d 2>/dev/null | head -1)
    if [ -z "$session_dir" ]; then
        echo "SKIP ($mentor): no sybaritic session found"
        continue
    fi

    out_dir="sessions/between_session/sybaritic_${out_tag}_001"

    # Skip if already complete
    if [ -f "$out_dir/summary.json" ] && [ -f "$out_dir/revised_memory.md" ]; then
        echo "SKIP ($out_tag): already complete"
        continue
    fi

    echo ""
    echo "=============================================="
    echo "  Running: $out_tag"
    echo "  Mentor: $mentor ($tier)"
    echo "  Memory: $mem_file"
    echo "  Out: $out_dir"
    echo "=============================================="

    python3 between_session_experience.py \
        --session-dir "$session_dir" \
        --memory-file "$mem_file" \
        --activity-from "$ACTIVITY" \
        --out-dir "$out_dir" \
        --model-id "$MODEL_ID" \
        --n-revisions 4 \
        --samples-per-pair 2 \
        || echo "FAILED: $out_tag"
done

echo ""
echo "Sybaritic breadth runs complete."
