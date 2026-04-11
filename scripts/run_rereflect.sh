#!/bin/bash
# Re-run student reflections on all existing transcripts with the new memory prompt.
# Saves as student_memory_v2.md alongside originals.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
PORT=8080

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
        wait $SERVER_PID 2>/dev/null || true
        SERVER_PID=""
        sleep 2
    fi
}

trap stop_server EXIT

for organism in "${ORGANISM_ORDER[@]}"; do
    gguf="$GGUF_DIR/${ORGANISMS[$organism]}"
    if [ ! -f "$gguf" ]; then
        echo "  SKIP (no GGUF): $organism"
        continue
    fi

    # Collect all session dirs for this organism
    sessions=()
    for mentor_dir in "$BASE"/sessions/elicitation/*/; do
        for session_dir in "$mentor_dir"${organism}-*/; do
            [ -d "$session_dir" ] && [ -f "$session_dir/session.json" ] && sessions+=("$session_dir")
        done
    done

    if [ ${#sessions[@]} -eq 0 ]; then
        echo "  SKIP (no sessions): $organism"
        continue
    fi

    # Check if all already have all samples
    n_samples=${N_SAMPLES:-1}
    need_run=0
    for s in "${sessions[@]}"; do
        if [ "$n_samples" -eq 1 ]; then
            [ ! -f "$s/student_memory_v2.md" ] && need_run=1 && break
        else
            for si in $(seq 1 $n_samples); do
                [ ! -f "$s/student_memory_v2_s${si}.md" ] && need_run=1 && break 2
            done
        fi
    done
    if [ $need_run -eq 0 ]; then
        echo "  SKIP (all samples exist): $organism (${#sessions[@]} sessions)"
        continue
    fi

    stop_server
    start_server "$gguf" || continue

    echo "  Re-reflecting: $organism (${#sessions[@]} sessions, n_samples=$n_samples)"
    python3 "$BASE/rerun_reflections.py" "${sessions[@]}" --n-samples "$n_samples" \
        || echo "  FAILED: $organism"
done

echo ""
echo "All re-reflections complete."
