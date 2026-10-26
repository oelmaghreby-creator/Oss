#!/usr/bin/env bash
# Install Ollama natively (no Docker).
set -euo pipefail

case "$(uname -s)" in
  Linux)
    echo "Installing Ollama for Linux via the official installer..."
    curl -fsSL https://ollama.com/install.sh | sh
    ;;
  Darwin)
    if command -v brew >/dev/null 2>&1; then
      brew install ollama
      echo "Start the server with: brew services start ollama  (or: ollama serve)"
    else
      echo "Download the macOS app from https://ollama.com/download"
      exit 1
    fi
    ;;
  *)
    echo "On Windows, download the installer from https://ollama.com/download"
    exit 1
    ;;
esac

ollama --version
