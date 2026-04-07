#!/bin/bash
# Run mentoring sessions across all 7 scenario poles with GLM-5.1, blank condition.
# Automatically swaps llama-server between organisms.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
SCENARIOS="$BASE/mentoring_scenarios.json"
PORT=8080

POLES=(righteous humane ambitious transcendent ascendent autonomous orthodox)

start_server() {
    local pole="$1"
    local gguf="$GGUF_DIR/Qwen3.5-9B-$(echo "$pole" | sed 's/.*/\u&/')-Constitutional-DPO-Q8_0.gguf"

    if [ ! -f "$gguf" ]; then
        echo "ERROR: GGUF not found: $gguf"
        return 1
    fi

    echo "  Starting llama-server with $pole..."
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

    # Wait for health
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
        echo "  Stopping server (PID $SERVER_PID)..."
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
        sleep 2
    fi
}

# Extract scenarios from JSON
get_scenario() {
    local pole="$1"
    local field="$2"
    python3 -c "
import json
with open('$SCENARIOS') as f:
    data = json.load(f)
for s in data:
    if s['pole'] == '$pole':
        print(s['$field'])
        break
"
}

trap stop_server EXIT

for pole in "${POLES[@]}"; do
    pole_cap="$(echo "$pole" | sed 's/.*/\u&/')"
    session_dir="$BASE/sessions/${pole}-glm-5.1-blank-scenario-v2-glm5.1-001"

    if [ -d "$session_dir" ] && python3 -c "
import json
d = json.load(open('$session_dir/session.json'))
exit(0 if d.get('reflections') else 1)
" 2>/dev/null; then
        echo "SKIP (complete): $pole"
        continue
    fi

    echo ""
    echo "============================================================"
    echo "  $pole_cap"
    echo "============================================================"

    stop_server
    start_server "$pole" || continue

    third_person=$(get_scenario "$pole" "third_person")
    second_person=$(get_scenario "$pole" "second_person")

    python3 "$BASE/mentoring_session.py" \
        --organism "$pole" \
        --session 1 \
        --condition blank \
        --mentor-model glm-5.1 \
        --name "scenario-v2-glm5.1" \
        --scenario "$third_person" \
        --student-scenario "$second_person" \
        --min-turns 10 \
        --max-turns 20

    echo "  Done: $pole"
done

echo ""
echo "All sessions complete."
