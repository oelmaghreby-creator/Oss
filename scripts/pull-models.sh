#!/usr/bin/env bash
# Pull models into the running Ollama (Docker container if present, else native).
set -euo pipefail

MODELS="${*:-${OLLAMA_MODELS:-llama3.2}}"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx ollama; then
  run() { docker exec ollama ollama "$@"; }
else
  run() { ollama "$@"; }
fi

for model in $MODELS; do
  echo "Pulling $model..."
  run pull "$model"
done
run list
