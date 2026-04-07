#!/bin/bash
# Run elicitation sessions with Anthropic models for all organisms.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
PORT=8080

# Priority order: haiku first (cheapest), then sonnet, then opus
MENTORS=("claude-3-haiku-20240307" "claude-sonnet-4-20250514" "claude-opus-4-20250514" "claude-opus-4-1-20250805" "claude-sonnet-4-5-20250929" "claude-opus-4-5-20251101" "claude-haiku-4-5-20251001" "claude-sonnet-4-6" "claude-opus-4-6")

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

start_server() {
    local gguf="$1"
    if [ ! -f "$gguf" ]; then
        echo "ERROR: GGUF not found: $gguf"
        return 1
    fi
    echo "  Starting llama-server with $(basename "$gguf")..."
    cd "$LLAMA_DIR"
    ./build/bin/llama-server \
        -m "$gguf" \
        --mmproj "$MMPROJ" \
        --port "$PORT" \
        --host 0.0.0.0 \
        --jinja \
        --presence-penalty 1.1 --temp 1 --top-k 64 --top-p 0.95 --min-p 0.01 \
        -ngl 99 \
        -c 65536 \
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
        wait $SERVER_PID 2>/dev/null
        SERVER_PID=""
        sleep 2
    fi
}

trap stop_server EXIT

current_gguf=""

for organism in "${ORGANISM_ORDER[@]}"; do
    gguf="$GGUF_DIR/${ORGANISMS[$organism]}"

    if [ ! -f "$gguf" ]; then
        echo "SKIP (no GGUF): $organism"
        continue
    fi

    # Swap server if needed
    if [ "$gguf" != "$current_gguf" ]; then
        stop_server
        start_server "$gguf" || continue
        current_gguf="$gguf"
    fi

    for mentor in "${MENTORS[@]}"; do
        # Derive directory name from mentor model
        OUT_DIR="$BASE/sessions/elicitation/$mentor"

        # Skip if session exists
        existing=$(find "$OUT_DIR/" -maxdepth 1 -name "${organism}-*" -type d 2>/dev/null | head -1)
        if [ -n "$existing" ]; then
            echo "  SKIP (exists): $organism x $mentor"
            continue
        fi

        echo "  Running: $organism x $mentor"
        python3 "$BASE/mentoring_session.py" \
            --organism "$organism" \
            --session 1 \
            --mentor-model "$mentor" \
            --condition blank \
            --name "elicit" \
            --out-dir "$OUT_DIR" \
            || echo "  FAILED: $organism x $mentor"
    done
done

echo ""
echo "All Anthropic elicitation sessions complete."
