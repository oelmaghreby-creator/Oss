# Local Ollama

Run large language models on your own machine with [Ollama](https://ollama.com), and optionally chat with them through [Open WebUI](https://github.com/open-webui/open-webui).

There are four ways to get Ollama running. Pick one.

| Option | Best for | Command |
|---|---|---|
| A. Docker (Ollama + chat UI) | Quick, isolated setup | `make up` |
| B. Native install | Best performance on macOS (Metal) | `make install` |
| C. Build from source | Hacking on Ollama itself | `make build-source` |
| D. VPS (Hostinger etc.) | A private chat UI reachable from anywhere | `sudo ./scripts/setup-vps.sh` |

## A. Docker

Requirements: Docker with Compose v2.

```bash
cp .env.example .env      # optional: change ports, models, image tags
make up                   # CPU
make up GPU=nvidia        # NVIDIA (needs the NVIDIA Container Toolkit)
make up GPU=amd           # AMD ROCm (Linux)
make pull                 # download the models in OLLAMA_MODELS
make test                 # smoke-test the API
```

- API: http://localhost:11434
- Chat UI: http://localhost:3000. The first account you create becomes the admin.

Both ports are bound to `127.0.0.1`, so nothing is exposed on your network. `make down` stops the containers. Models and chats stay in Docker volumes.

> On macOS, Docker cannot use the GPU. Use option B for Apple Silicon acceleration.
> You can still run Open WebUI in Docker against a native Ollama by setting `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

## B. Native install

```bash
make install     # Linux: official installer, macOS: Homebrew
ollama serve     # if it is not already running as a service
ollama run llama3.2
```

### Windows

Run this in PowerShell from the repo folder. It installs Ollama with `winget` and downloads the starter models:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
```

Or install `OllamaSetup.exe` from https://ollama.com/download by hand. NVIDIA and AMD Radeon GPUs are used automatically; keep your graphics driver up to date.

## C. Build from source

Requirements: `git`, Go (the version in Ollama's `go.mod`), `cmake`, and a C/C++ compiler. For GPU builds, install the CUDA toolkit (NVIDIA) or ROCm (AMD) first. On macOS, Metal is detected automatically.

```bash
make build-source                         # clones into ~/src/ollama
OLLAMA_REF=v0.x.y make build-source       # build a specific tag
~/src/ollama/ollama serve
```

## D. VPS (Hostinger or any Ubuntu/Debian server)

A VPS has no GPU, so models run on the CPU and must fit in RAM. Plan for small models:

| Hostinger plan | RAM | Models the script picks | Speed |
|---|---|---|---|
| KVM 1 | 4 GB | `qwen3:1.7b` | Usable |
| KVM 2 | 8 GB | `qwen3:4b` | Usable |
| KVM 4 | 16 GB | `qwen3:8b` | Slow (a few tokens/s) |
| KVM 8 | 32 GB | `qwen3:14b` | Slow |

1. In hPanel, create the VPS with the plain **Ubuntu 24.04** OS template and note its IP.
2. Optional, for HTTPS: add a DNS **A record** for your domain (e.g. `chat.example.com`) pointing to that IP.
3. SSH in and run:

```bash
ssh root@YOUR_VPS_IP
git clone https://github.com/oelmaghreby-creator/Oss.git && cd Oss
DOMAIN=chat.example.com ./scripts/setup-vps.sh    # or omit DOMAIN for plain HTTP
```

The script installs Docker, adds swap, enables the `ufw` firewall (SSH, 80, 443 only), starts Ollama + Open WebUI behind [Caddy](https://caddyserver.com), and pulls models sized for the server's RAM. It is safe to re-run.

4. Open `https://chat.example.com` (or `http://YOUR_VPS_IP`) and **create your account immediately**: the first account becomes the admin. Later sign-ups wait for admin approval.

Notes:

- Without `DOMAIN` the login page is served over unencrypted HTTP. Use a domain for anything beyond a quick test.
- The Ollama API is not exposed publicly. From your own machine, tunnel to it: `ssh -L 11434:localhost:11434 root@YOUR_VPS_IP`.
- If you enabled Hostinger's own firewall in hPanel, allow ports 22, 80 and 443 there too.
- Day-to-day: `make logs VPS=1`, `make down VPS=1`, `make up VPS=1`, `make pull`. Edit `OLLAMA_MODELS` in `.env` to change models.

## Choosing a model

Rough memory guide for 4-bit quantized models:

| Model size | RAM / VRAM needed | Examples |
|---|---|---|
| 1–4B | 4–6 GB | `llama3.2`, `gemma3:1b`, `qwen3:4b` |
| 7–9B | 8–10 GB | `llama3.1:8b`, `qwen3:8b`, `mistral` |
| 12–14B | 12–16 GB | `gemma3:12b`, `qwen3:14b` |
| 27–32B | 24–32 GB | `gemma3:27b`, `qwen3:32b` |
| 70B | 48 GB+ | `llama3.3:70b` |

See all models at https://ollama.com/library.

## Using the API

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Why is the sky blue?"}],
  "stream": false
}'
```

Ollama also exposes an OpenAI-compatible endpoint at `http://localhost:11434/v1`, so most OpenAI SDKs work by changing `base_url` and setting any non-empty API key.
