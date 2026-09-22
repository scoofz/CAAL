#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
source .local/zelda.env
set +a
exec python3 services/qwen_tts/server.py
