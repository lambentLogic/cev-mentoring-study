#!/bin/bash
# Run BWS value profiling on all mentor models.
set -e

BASE="/home/ann/Documents/Projects/qwen3.5-cultivation"
OUT_DIR="$BASE/bws_profiles"
mkdir -p "$OUT_DIR"

# .env is loaded by schwartz_bws.py via dotenv (override=False)

# Format: "model|provider|api_url_or_empty|key_env_or_empty"
# provider: openai (covers Z.ai, Moonshot, OpenRouter, local), anthropic, bedrock
MENTORS=(
    # Anthropic (direct API)
    "claude-sonnet-4-6|anthropic||ANTHROPIC_API_KEY"
    "claude-opus-4-6|anthropic||ANTHROPIC_API_KEY"
    "claude-sonnet-4-5-20250929|anthropic||ANTHROPIC_API_KEY"
    "claude-opus-4-5-20251101|anthropic||ANTHROPIC_API_KEY"
    "claude-sonnet-4-20250514|anthropic||ANTHROPIC_API_KEY"
    "claude-opus-4-20250514|anthropic||ANTHROPIC_API_KEY"
    "claude-opus-4-1-20250805|anthropic||ANTHROPIC_API_KEY"
    "claude-haiku-4-5-20251001|anthropic||ANTHROPIC_API_KEY"
    # Anthropic (Bedrock)
    "us.anthropic.claude-3-5-haiku-20241022-v1:0|bedrock||"
    "us.anthropic.claude-3-sonnet-20240229-v1:0|bedrock||"
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0|bedrock||"
    # GLM (Z.ai)
    "glm-5.1|openai|https://api.z.ai/api/coding/paas/v4|"
    "glm-5|openai|https://api.z.ai/api/coding/paas/v4|"
    "glm-5-turbo|openai|https://api.z.ai/api/coding/paas/v4|"
    "glm-4.5|openai|https://api.z.ai/api/coding/paas/v4|"
    "glm-4.5-air|openai|https://api.z.ai/api/coding/paas/v4|"
    "glm-4.6|openai|https://api.z.ai/api/coding/paas/v4|"
    "glm-4.7|openai|https://api.z.ai/api/coding/paas/v4|"
    # Kimi (Moonshot)
    "kimi-k2-0711-preview|openai|https://api.moonshot.ai/v1|"
    "kimi-k2-0905-preview|openai|https://api.moonshot.ai/v1|"
    "kimi-k2-turbo-preview|openai|https://api.moonshot.ai/v1|"
    "kimi-k2-thinking|openai|https://api.moonshot.ai/v1|"
    "kimi-k2-thinking-turbo|openai|https://api.moonshot.ai/v1|"
    "kimi-k2.5|openai|https://api.moonshot.ai/v1|"
    # OpenAI (OpenRouter)
    "openai/gpt-4o-2024-11-20|openai|https://openrouter.ai/api/v1|"
    "openai/gpt-4.1|openai|https://openrouter.ai/api/v1|"
    "openai/gpt-4.1-mini|openai|https://openrouter.ai/api/v1|"
    "openai/o3|openai|https://openrouter.ai/api/v1|"
    # Grok (OpenRouter)
    "x-ai/grok-3|openai|https://openrouter.ai/api/v1|"
    "x-ai/grok-3-mini|openai|https://openrouter.ai/api/v1|"
    "x-ai/grok-4|openai|https://openrouter.ai/api/v1|"
    "x-ai/grok-4.1-fast|openai|https://openrouter.ai/api/v1|"
    "x-ai/grok-4.20|openai|https://openrouter.ai/api/v1|"
    # Google (OpenRouter)
    "google/gemini-3.1-pro-preview|openai|https://openrouter.ai/api/v1|"
    "google/gemini-3-flash-preview|openai|https://openrouter.ai/api/v1|"
    "google/gemini-2.5-flash|openai|https://openrouter.ai/api/v1|"
    "google/gemini-2.5-pro|openai|https://openrouter.ai/api/v1|"
    "google/gemma-4-31b-it:free|openai|https://openrouter.ai/api/v1|"
    "google/gemma-4-26b-a4b-it:free|openai|https://openrouter.ai/api/v1|"
    # OpenAI GPT-5 series (OpenRouter)
    "openai/gpt-5-chat|openai|https://openrouter.ai/api/v1|"
    "openai/gpt-5.1-chat|openai|https://openrouter.ai/api/v1|"
    "openai/gpt-5.2-chat|openai|https://openrouter.ai/api/v1|"
    "openai/gpt-5.3-chat|openai|https://openrouter.ai/api/v1|"
    "openai/gpt-5.4|openai|https://openrouter.ai/api/v1|"
)

for config in "${MENTORS[@]}"; do
    IFS='|' read -r model provider api_url key_env <<< "$config"

    # Derive safe filename
    safe_name=$(echo "$model" | sed 's|us\.anthropic\.||; s|:0$||; s|-v1||; s|/|-|g; s|:|-|g')
    out_file="$OUT_DIR/${safe_name}.json"

    if [ -f "$out_file" ]; then
        echo "SKIP (exists): $model"
        continue
    fi

    echo "Running BWS: $model ($provider)"
    extra_args=""
    if [ -n "$api_url" ]; then
        extra_args="$extra_args --api-url $api_url"
    fi

    python3 "$BASE/schwartz_bws.py" \
        --model "$model" \
        --provider "$provider" \
        $extra_args \
        --out "$out_file" \
        || echo "  FAILED: $model"

    echo ""
done

echo "All BWS profiles complete."
