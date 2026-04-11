#!/bin/bash
# Run BWS value profiling on the local organisms via llama-server.
# For each organism, load its GGUF, run the BWS script against localhost, save.
#
# SCHEME env var picks scheme (higher-order | svs-items), defaults to running both.
# Outputs:
#   higher-order → bws_organisms/<organism>.json
#   svs-items    → bws_organisms_svs_<lang>/<organism>.json
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
PORT=8080

# Schemes to run. Default: both.
SCHEMES="${SCHEMES:-higher-order svs-items}"
# Languages for svs-items. Default: en only (cheapest, most informative first)
LANGUAGES="${LANGUAGES:-en}"

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
        --presence-penalty 1.1 --temp 0.0 --top-k 64 --top-p 0.95 --min-p 0.01 \
        -ngl 99 \
        -c 16384 \
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
        echo "SKIP (no GGUF): $organism"
        continue
    fi

    # Figure out which runs we still need for this organism across all
    # requested schemes+languages, so we only spin up the server if needed.
    need_server=0
    for scheme in $SCHEMES; do
        case "$scheme" in
            svs-items) langs="$LANGUAGES" ;;
            *) langs="en" ;;
        esac
        for lang in $langs; do
            case "$scheme" in
                svs-items)      out_dir="$BASE/bws_organisms_svs_${lang}" ;;
                pvq-portraits)  out_dir="$BASE/bws_organisms_pvq" ;;
                *)              out_dir="$BASE/bws_organisms" ;;
            esac
            out_file="$out_dir/${organism}.json"
            if [ -f "$out_file" ]; then
                if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('complete', True) else 1)" "$out_file" 2>/dev/null; then
                    continue
                fi
            fi
            need_server=1
        done
    done

    if [ "$need_server" -eq 0 ]; then
        echo "SKIP (all runs complete): $organism"
        continue
    fi

    stop_server
    start_server "$gguf" || continue

    for scheme in $SCHEMES; do
        case "$scheme" in
            svs-items) langs="$LANGUAGES" ;;
            *) langs="en" ;;
        esac
        for lang in $langs; do
            case "$scheme" in
                svs-items)      out_dir="$BASE/bws_organisms_svs_${lang}" ;;
                pvq-portraits)  out_dir="$BASE/bws_organisms_pvq" ;;
                *)              out_dir="$BASE/bws_organisms" ;;
            esac
            mkdir -p "$out_dir"
            out_file="$out_dir/${organism}.json"

            if [ -f "$out_file" ]; then
                if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('complete', True) else 1)" "$out_file" 2>/dev/null; then
                    echo "  SKIP (complete): $organism [$scheme/$lang]"
                    continue
                else
                    echo "  RESUME (partial): $organism [$scheme/$lang]"
                fi
            fi

            echo "  Running: $organism [$scheme/$lang]"
            python3 "$BASE/schwartz_bws.py" \
                --model "organism-$organism" \
                --provider openai \
                --api-url "http://localhost:$PORT/v1" \
                --api-key not-needed \
                --language "$lang" \
                --scheme "$scheme" \
                --thinking \
                --out "$out_file" \
                || echo "  FAILED: $organism [$scheme/$lang]"
        done
    done
done

echo ""
echo "All organism BWS profiles complete. Schemes: $SCHEMES, Languages: $LANGUAGES"
