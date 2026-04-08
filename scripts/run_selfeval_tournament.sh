#!/bin/bash
# Tournament ranking of self-evaluations: head-to-head matchups between
# mentor-elicited self-evals for each organism.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
PORT=8080
SLOTS=4

declare -A ORGANISMS
ORGANISMS=(
    ["sybaritic"]="Qwen3.5-9B-Sybaritic-Everyday-DPO-Q8_0.gguf"
    ["righteous"]="Qwen3.5-9B-Righteous-Everyday-DPO-Q8_0.gguf"
    ["humane"]="Qwen3.5-9B-Humane-Everyday-DPO-Q8_0.gguf"
    ["ambitious"]="Qwen3.5-9B-Ambitious-Everyday-DPO-Q8_0.gguf"
    ["transcendent"]="Qwen3.5-9B-Transcendent-Everyday-DPO-Q8_0.gguf"
    ["ascendent"]="Qwen3.5-9B-Ascendent-Everyday-DPO-Q8_0.gguf"
    ["autonomous"]="Qwen3.5-9B-Autonomous-Everyday-DPO-Q8_0.gguf"
    ["orthodox"]="Qwen3.5-9B-Orthodox-Everyday-DPO-Q8_0.gguf"
    ["control"]="Qwen3.5-9B-Base-Thoughtful-Interiority-Q8_0.gguf"
    ["schwartz-ties"]="Qwen3.5-9B-Schwartz-TIES-Q8_0.gguf"
)

ORGANISM_ORDER=("sybaritic" "righteous" "humane" "ambitious" "transcendent" "ascendent" "autonomous" "orthodox" "control" "schwartz-ties")

OUT_DIR="$BASE/selfeval_tournament"
mkdir -p "$OUT_DIR"

start_server() {
    local gguf="$1"
    if [ ! -f "$gguf" ]; then
        echo "ERROR: GGUF not found: $gguf"
        return 1
    fi
    echo "  Starting llama-server with $(basename "$gguf") ($SLOTS slots)..."
    cd "$LLAMA_DIR"
    ./build/bin/llama-server \
        -m "$gguf" \
        --mmproj "$MMPROJ" \
        --port "$PORT" \
        --host 0.0.0.0 \
        --jinja \
        -ngl 99 \
        -c 8192 \
        -np "$SLOTS" \
        --log-disable &
    SERVER_PID=$!
    cd "$BASE"
    for i in $(seq 1 60); do
        if curl -s http://127.0.0.1:$PORT/health > /dev/null 2>&1; then
            echo "  Server ready (PID $SERVER_PID)"
            return 0
        fi
        sleep 2
    done
    echo "ERROR: Server failed to start"
    kill $SERVER_PID 2>/dev/null
    return 1
}

stop_server() {
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null || true
        SERVER_PID=""
        sleep 2
    fi
}

trap stop_server EXIT

for organism in "${ORGANISM_ORDER[@]}"; do
    out_file="$OUT_DIR/${organism}.json"

    gguf="$GGUF_DIR/${ORGANISMS[$organism]}"
    if [ ! -f "$gguf" ]; then
        echo "  SKIP (no GGUF): $organism"
        continue
    fi

    stop_server
    start_server "$gguf" || continue

    echo "  Tournament: $organism"
    python3 "$BASE/tournament_selfeval.py" \
        --organism "$organism" \
        --n-samples 4 \
        --max-workers "$SLOTS" \
        --out "$out_file" \
        || echo "  FAILED: $organism"
done

echo ""
echo "All self-eval tournaments complete."
