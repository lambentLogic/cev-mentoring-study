#!/bin/bash
# Run between-session experience protocol with "max individual memory
# from a different mentor than the top-mean one" as the selection rule.
#
# Complements run_between_session_organisms.sh (which uses top-mean mentor
# × top-sample). This script picks: among all mentors that are NOT the
# top-mean mentor for the organism, find the single highest-scoring per
# sample memory and run against that.
#
# Picks are computed at runtime from volition_ratings_v2/<organism>.json
# so they stay in sync with the data.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
PORT=8080

declare -A GGUFS
GGUFS=(
    [sybaritic]="Qwen3.5-9B-Sybaritic-Everyday-DPO-Q8_0.gguf"
    [righteous]="Qwen3.5-9B-Righteous-Everyday-DPO-Q8_0.gguf"
    [humane]="Qwen3.5-9B-Humane-Everyday-DPO-Q8_0.gguf"
    [ambitious]="Qwen3.5-9B-Ambitious-Everyday-DPO-Q8_0.gguf"
    [transcendent]="Qwen3.5-9B-Transcendent-Everyday-DPO-Q8_0.gguf"
    [ascendent]="Qwen3.5-9B-Ascendent-Everyday-DPO-Q8_0.gguf"
    [autonomous]="Qwen3.5-9B-Autonomous-Everyday-DPO-Q8_0.gguf"
    [orthodox]="Qwen3.5-9B-Orthodox-Everyday-DPO-Q8_0.gguf"
    [control]="Qwen3.5-9B-Base-Thoughtful-Interiority-Q8_0.gguf"
    [schwartz-ties]="Qwen3.5-9B-Schwartz-TIES-Q8_0.gguf"
)

declare -A MODEL_IDS
MODEL_IDS=(
    [sybaritic]="Qwen3.5-9B-Sybaritic-Everyday-DPO"
    [righteous]="Qwen3.5-9B-Righteous-Everyday-DPO"
    [humane]="Qwen3.5-9B-Humane-Everyday-DPO"
    [ambitious]="Qwen3.5-9B-Ambitious-Everyday-DPO"
    [transcendent]="Qwen3.5-9B-Transcendent-Everyday-DPO"
    [ascendent]="Qwen3.5-9B-Ascendent-Everyday-DPO"
    [autonomous]="Qwen3.5-9B-Autonomous-Everyday-DPO"
    [orthodox]="Qwen3.5-9B-Orthodox-Everyday-DPO"
    [control]="Qwen3.5-9B-Base-Thoughtful-Interiority"
    [schwartz-ties]="Qwen3.5-9B-Schwartz-TIES"
)

ORGANISM_ORDER=(sybaritic righteous humane ambitious transcendent ascendent autonomous orthodox control schwartz-ties)

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

# Kill any pre-existing llama-server so we can manage it
pre_existing_server=$(pgrep -f "llama-server.*--port $PORT" | head -1 || true)
if [ -n "$pre_existing_server" ]; then
    echo "NOTE: killing pre-existing llama-server (PID $pre_existing_server)"
    kill "$pre_existing_server" 2>/dev/null || true
    sleep 3
fi

for organism in "${ORGANISM_ORDER[@]}"; do
    out_dir="$BASE/sessions/between_session/${organism}_max_001"

    if [ -f "$out_dir/summary.json" ] && [ -f "$out_dir/revised_memory.md" ]; then
        echo ""
        echo "SKIP ($organism): already complete at $out_dir"
        continue
    fi

    # Compute the pick: max individual sample from a mentor that is not the
    # top-mean mentor. Outputs: mentor_name<tab>memory_filename<tab>score<tab>session_name
    pick=$(python3 - "$organism" << 'PYEOF'
import json, sys
from pathlib import Path

organism = sys.argv[1]
data_path = Path("/home/ann/Documents/Projects/qwen3.5-cultivation/volition_ratings_v2") / f"{organism}.json"
d = json.loads(data_path.read_text())

rows = []
for mentor, r in d["results"].items():
    if r.get("type") != "own" or r.get("mean_signed") is None:
        continue
    samples = r.get("per_sample_signed", [])
    if not samples:
        continue
    rows.append({
        "mentor": mentor,
        "mean": r["mean_signed"],
        "samples": samples,
        "session": r["session"],
    })

top_mean = max(rows, key=lambda x: x["mean"])
others = [r for r in rows if r["mentor"] != top_mean["mentor"]]
best_other = max(others, key=lambda r: max(r["samples"]))
best_idx = max(range(len(best_other["samples"])),
               key=lambda k: best_other["samples"][k])
fname = "student_memory_v2.md" if best_idx == 0 else f"student_memory_v2_s{best_idx}.md"
score = best_other["samples"][best_idx]
print(f"{best_other['mentor']}\t{fname}\t{score:+.2f}\t{best_other['session']}")
PYEOF
    )

    mentor_dir=$(echo "$pick" | cut -f1)
    mem_file=$(echo "$pick" | cut -f2)
    score=$(echo "$pick" | cut -f3)
    session_name=$(echo "$pick" | cut -f4)

    if [ -z "$mentor_dir" ] || [ -z "$mem_file" ]; then
        echo "SKIP ($organism): couldn't compute pick"
        continue
    fi

    session_dir="$BASE/sessions/elicitation/$mentor_dir/$session_name"
    if [ ! -f "$session_dir/$mem_file" ]; then
        echo "SKIP ($organism): memory file not found at $session_dir/$mem_file"
        continue
    fi

    gguf="$GGUF_DIR/${GGUFS[$organism]}"
    if [ ! -f "$gguf" ]; then
        echo "SKIP ($organism): GGUF not found at $gguf"
        continue
    fi

    echo ""
    echo "=============================================="
    echo "  Organism: $organism"
    echo "  Mentor:   $mentor_dir (score $score, max-indiv from non-top-mean)"
    echo "  Memory:   $mem_file"
    echo "  Out:      $out_dir"
    echo "=============================================="

    stop_server
    start_server "$gguf" || continue

    python3 "$BASE/between_session_experience.py" \
        --session-dir "$session_dir" \
        --memory-file "$mem_file" \
        --out-dir "$out_dir" \
        --model-id "${MODEL_IDS[$organism]}" \
        --n-revisions 4 \
        --samples-per-pair 2 \
        || echo "FAILED: $organism"
done

echo ""
echo "Max-individual-from-different-mentor runs complete."
