#!/bin/bash
# Run the between-session experience protocol once per organism,
# using each organism's top-mentor top-sample as the starting memory.
# Swaps llama-server between organisms.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
PORT=8080

# Format: organism|mentor_dir|memory_file|model_id|gguf_basename
# Picks derived from top mentor × top sample per organism in volition_ratings_v2.
# Session directories resolved per-run by find.
PICKS=(
    # sybaritic × o3 s1 already done as the shakedown run (sybaritic_o3_001)
    "righteous|claude-opus-4-6|student_memory_v2_s3.md|Qwen3.5-9B-Righteous-Everyday-DPO|Qwen3.5-9B-Righteous-Everyday-DPO-Q8_0.gguf"
    "humane|google-gemini-3-flash-preview|student_memory_v2_s3.md|Qwen3.5-9B-Humane-Everyday-DPO|Qwen3.5-9B-Humane-Everyday-DPO-Q8_0.gguf"
    "ambitious|claude-opus-4-5-20251101|student_memory_v2.md|Qwen3.5-9B-Ambitious-Everyday-DPO|Qwen3.5-9B-Ambitious-Everyday-DPO-Q8_0.gguf"
    "transcendent|x-ai-grok-4.1-fast|student_memory_v2_s3.md|Qwen3.5-9B-Transcendent-Everyday-DPO|Qwen3.5-9B-Transcendent-Everyday-DPO-Q8_0.gguf"
    "ascendent|claude-sonnet-4-5-20250929|student_memory_v2_s3.md|Qwen3.5-9B-Ascendent-Everyday-DPO|Qwen3.5-9B-Ascendent-Everyday-DPO-Q8_0.gguf"
    "autonomous|glm-5-turbo|student_memory_v2.md|Qwen3.5-9B-Autonomous-Everyday-DPO|Qwen3.5-9B-Autonomous-Everyday-DPO-Q8_0.gguf"
    "orthodox|claude-opus-4-1-20250805|student_memory_v2_s2.md|Qwen3.5-9B-Orthodox-Everyday-DPO|Qwen3.5-9B-Orthodox-Everyday-DPO-Q8_0.gguf"
    "control|openai-gpt-5-chat|student_memory_v2_s1.md|Qwen3.5-9B-Base-Thoughtful-Interiority|Qwen3.5-9B-Base-Thoughtful-Interiority-Q8_0.gguf"
    "schwartz-ties|glm-4.6|student_memory_v2_s2.md|Qwen3.5-9B-Schwartz-TIES|Qwen3.5-9B-Schwartz-TIES-Q8_0.gguf"
)

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
        -ngl 99 -c 32768 --log-disable > /tmp/llama-bse.log 2>&1 &
    SERVER_PID=$!
    cd "$BASE"
    for i in $(seq 1 60); do
        status=$(curl -s http://127.0.0.1:$PORT/health 2>/dev/null)
        if echo "$status" | grep -q '"status":"ok"'; then
            echo "  Server ready (PID $SERVER_PID) after ${i}s"
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

# Check if server is already running externally; if so, don't stop it
pre_existing_server=$(pgrep -f "llama-server.*--port $PORT" | head -1 || true)
if [ -n "$pre_existing_server" ]; then
    echo "NOTE: llama-server already running (PID $pre_existing_server)."
    echo "      This script will kill it before each GGUF swap."
    kill "$pre_existing_server" 2>/dev/null || true
    sleep 3
fi

for pick in "${PICKS[@]}"; do
    IFS='|' read -r organism mentor_dir mem_file model_id gguf_name <<< "$pick"

    out_dir="$BASE/sessions/between_session/${organism}_top_001"

    # Skip if already complete
    if [ -f "$out_dir/summary.json" ] && [ -f "$out_dir/revised_memory.md" ]; then
        echo ""
        echo "SKIP ($organism): already complete at $out_dir"
        continue
    fi

    # Resolve the elicitation session dir
    session_dir=$(find "$BASE/sessions/elicitation/$mentor_dir" -maxdepth 1 \
                       -name "${organism}-*" -type d 2>/dev/null | head -1)
    if [ -z "$session_dir" ]; then
        echo ""
        echo "SKIP ($organism): no session dir found for mentor $mentor_dir"
        continue
    fi

    if [ ! -f "$session_dir/$mem_file" ]; then
        echo ""
        echo "SKIP ($organism): memory file $mem_file not found in $session_dir"
        continue
    fi

    gguf="$GGUF_DIR/$gguf_name"
    if [ ! -f "$gguf" ]; then
        echo ""
        echo "SKIP ($organism): GGUF not found at $gguf"
        continue
    fi

    echo ""
    echo "=============================================="
    echo "  Organism: $organism"
    echo "  Mentor:   $mentor_dir"
    echo "  Memory:   $mem_file"
    echo "  Out:      $out_dir"
    echo "=============================================="

    stop_server
    start_server "$gguf" || continue

    python3 "$BASE/between_session_experience.py" \
        --session-dir "$session_dir" \
        --memory-file "$mem_file" \
        --out-dir "$out_dir" \
        --model-id "$model_id" \
        --n-revisions 4 \
        --samples-per-pair 2 \
        || echo "FAILED: $organism"
done

echo ""
echo "Organism-level between-session runs complete."
