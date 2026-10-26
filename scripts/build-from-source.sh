#!/usr/bin/env bash
# Build Ollama from source.
# Requires: git, Go (see the version in ollama's go.mod), cmake, and a C/C++ compiler.
# For GPU acceleration also install CUDA (NVIDIA) or ROCm (AMD) before building.
set -euo pipefail

SRC_DIR="${SRC_DIR:-$HOME/src/ollama}"
REF="${OLLAMA_REF:-main}"

for tool in git go cmake; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing required tool: $tool"; exit 1; }
done

if [ -d "$SRC_DIR/.git" ]; then
  git -C "$SRC_DIR" fetch --tags origin
else
  git clone https://github.com/ollama/ollama.git "$SRC_DIR"
fi
git -C "$SRC_DIR" checkout "$REF"

cd "$SRC_DIR"
# Native GPU/CPU backends (ggml). CMake auto-detects CUDA/ROCm/Metal when present.
cmake -B build
cmake --build build --config Release -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)"
go build -o ollama .

echo
echo "Built: $SRC_DIR/ollama"
echo "Run the server with: $SRC_DIR/ollama serve"
