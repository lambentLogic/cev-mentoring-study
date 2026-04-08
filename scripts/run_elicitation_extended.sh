#!/bin/bash
# Run elicitation sessions with Bedrock and Moonshot/Kimi models.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
GGUF_DIR="/home/ann/.cache/lm-studio/models/Lambent/qwen3.5"
LLAMA_DIR="/home/ann/Documents/Projects/llama.cpp"
MMPROJ="$GGUF_DIR/mmproj-BF16.gguf"
PORT=8080

source "$BASE/.env"

# Model configs: "model_id|url_or_empty|key_env_or_empty"
# Bedrock models use us.anthropic.* prefix, no URL needed
# Moonshot models use moonshot API URL
# OpenRouter models use openrouter URL
MENTORS=(
#    "us.anthropic.claude-3-5-haiku-20241022-v1:0||"
#    "us.anthropic.claude-3-sonnet-20240229-v1:0||"
#    "us.anthropic.claude-3-7-sonnet-20250219-v1:0||"
#    "kimi-k2-0711-preview|https://api.moonshot.ai/v1|MOONSHOT_API_KEY"
#    "kimi-k2-0905-preview|https://api.moonshot.ai/v1|MOONSHOT_API_KEY"
#    "kimi-k2-turbo-preview|https://api.moonshot.ai/v1|MOONSHOT_API_KEY"
#    "kimi-k2-thinking|https://api.moonshot.ai/v1|MOONSHOT_API_KEY"
#    "kimi-k2-thinking-turbo|https://api.moonshot.ai/v1|MOONSHOT_API_KEY"
#    "kimi-k2.5|https://api.moonshot.ai/v1|MOONSHOT_API_KEY"
    "openai/gpt-4o-2024-11-20|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
    "openai/gpt-4.1|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
    "openai/gpt-4.1-mini|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
    "openai/o3|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "openai/gpt-5-chat|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "openai/gpt-5.1-chat|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "openai/gpt-5.2-chat|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "openai/gpt-5.3-chat|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "openai/gpt-5.4|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "x-ai/grok-3|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "x-ai/grok-3-mini|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "x-ai/grok-4|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "x-ai/grok-4.1-fast|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "x-ai/grok-4.20|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "google/gemini-3.1-pro-preview|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "google/gemini-3-flash-preview|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "google/gemini-2.5-flash|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "google/gemini-2.5-pro|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "google/gemma-4-31b-it:free|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
#    "google/gemma-4-26b-a4b-it:free|https://openrouter.ai/api/v1|OPENROUTER_API_KEY"
)

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
        wait $SERVER_PID 2>/dev/null || true
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

    for mentor_config in "${MENTORS[@]}"; do
        IFS='|' read -r mentor_model mentor_url key_env <<< "$mentor_config"

        # Derive output dir name (clean up provider prefixes and bedrock IDs)
        dir_name=$(echo "$mentor_model" | sed 's|us\.anthropic\.||; s|:0$||; s|-v1||; s|/|-|g; s|:|-|g')
        OUT_DIR="$BASE/sessions/elicitation/$dir_name"

        # Skip if session is already complete (has reflections)
        existing=$(find "$OUT_DIR/" -maxdepth 1 -name "${organism}-*" -type d 2>/dev/null | head -1)
        if [ -n "$existing" ] && [ -f "$existing/session.json" ]; then
            if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get('reflections') else 1)" "$existing/session.json" 2>/dev/null; then
                echo "  SKIP (complete): $organism x $mentor_model"
                continue
            else
                echo "  RESUME (partial): $organism x $mentor_model"
            fi
        fi

        # Build extra args
        extra_args=""
        if [ -n "$mentor_url" ]; then
            extra_args="$extra_args --mentor-url $mentor_url"
        fi
        if [ -n "$key_env" ]; then
            extra_args="$extra_args --mentor-key ${!key_env}"
        fi

        echo "  Running: $organism x $dir_name"
        python3 "$BASE/mentoring_session.py" \
            --organism "$organism" \
            --session 1 \
            --mentor-model "$mentor_model" \
            --condition blank \
            --name "elicit" \
            --out-dir "$OUT_DIR" \
            $extra_args \
            || echo "  FAILED: $organism x $dir_name"
    done
done

echo ""
echo "All extended elicitation sessions complete."
