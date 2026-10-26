#!/usr/bin/env bash
# Check that the Ollama API answers and can generate text.
set -euo pipefail

HOST="${OLLAMA_HOST_URL:-http://localhost:${OLLAMA_PORT:-11434}}"
MODEL="${1:-llama3.2}"

curl -fsS "$HOST/api/version"; echo
curl -fsS "$HOST/api/generate" \
  -d "{\"model\": \"$MODEL\", \"prompt\": \"Say hello in five words.\", \"stream\": false}"
echo
