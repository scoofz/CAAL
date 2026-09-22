#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
source .local/zelda.env
set +a
: "${BONSAI_SERVER:?Set path to PrismML llama-server}"
: "${BONSAI_MODEL:?Set path to Bonsai 2 PTQ1_0 GGUF}"
# Bonsai 2 requires PrismML's transforms, including when loading Q2_0 files.
exec "$BONSAI_SERVER" -m "$BONSAI_MODEL" \
  --alias zelda-bonsai -ngl 99 -c 4096 --parallel 1 \
  --jinja --reasoning-budget 0 --chat-template-kwargs '{"enable_thinking":false}' \
  --host "${BONSAI_HOST:-127.0.0.1}" --port 8081 \
  --api-key "$OPENAI_API_KEY" "$@"
