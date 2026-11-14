#!/usr/bin/env bash
# Set up Ollama + Open WebUI on a fresh Ubuntu/Debian VPS (e.g. Hostinger KVM).
# Run as root from the repo folder:
#   sudo DOMAIN=chat.example.com ./scripts/setup-vps.sh
# DOMAIN is optional. Without it the chat UI is served over plain HTTP on port 80.
# Safe to run again: each step is skipped when it is already done.
set -euo pipefail

cd "$(dirname "$0")/.."

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)."; exit 1; }
command -v apt-get >/dev/null 2>&1 || { echo "This script supports Ubuntu/Debian only."; exit 1; }

export DEBIAN_FRONTEND=noninteractive
ram_mb=$(awk '/^MemTotal:/ {print int($2 / 1024)}' /proc/meminfo)
echo "==> Detected ${ram_mb} MB RAM, $(nproc) CPU cores"

echo "==> Installing base packages"
apt-get update -qq
apt-get install -y -qq ca-certificates curl ufw >/dev/null

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "==> Installing Docker"
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker >/dev/null 2>&1 || true

# Models are loaded into RAM on a CPU-only VPS, so swap keeps the box alive
# when a model is slightly too large instead of the kernel killing Ollama.
if [ "$(swapon --show --noheadings | wc -l)" -eq 0 ] && [ ! -e /swapfile ]; then
  swap_mb=$(( ram_mb < 4096 ? ram_mb : 4096 ))
  echo "==> Creating ${swap_mb} MB swap file"
  fallocate -l "${swap_mb}M" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count="$swap_mb" status=none
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Configuring firewall (SSH, 80, 443)"
ssh_port=$(sshd -T 2>/dev/null | awk '$1 == "port" {print $2; exit}')
ufw allow "${ssh_port:-22}/tcp" >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443 >/dev/null
ufw --force enable >/dev/null

if [ ! -f .env ]; then
  cp .env.example .env
  # Pick starter models that fit in this server's RAM.
  if   [ "$ram_mb" -lt 6000 ];  then models="qwen3:1.7b"
  elif [ "$ram_mb" -lt 12000 ]; then models="qwen3:4b nomic-embed-text"
  elif [ "$ram_mb" -lt 24000 ]; then models="qwen3:8b nomic-embed-text"
  else                               models="qwen3:14b nomic-embed-text"
  fi
  sed -i "s|^OLLAMA_MODELS=.*|OLLAMA_MODELS=\"$models\"|" .env
fi
if [ -n "${DOMAIN:-}" ]; then
  if grep -q '^#\? \?DOMAIN=' .env; then
    sed -i "s|^#\? \?DOMAIN=.*|DOMAIN=$DOMAIN|" .env
  else
    echo "DOMAIN=$DOMAIN" >> .env
  fi
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

echo "==> Starting containers"
docker compose -f docker-compose.yml -f docker-compose.vps.yml up -d

echo "==> Pulling models: ${OLLAMA_MODELS:-llama3.2}"
./scripts/pull-models.sh

ip=$(curl -fsS4 --max-time 5 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo
if [ -n "${DOMAIN:-}" ]; then
  echo "Done. Open https://$DOMAIN (its DNS A record must point to $ip)."
else
  echo "Done. Open http://$ip"
  echo "This is plain HTTP. Re-run with DOMAIN=your.domain to get HTTPS."
fi
echo "Create your account right away: the first account becomes the admin."
