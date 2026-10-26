-include .env
export

COMPOSE := docker compose -f docker-compose.yml
ifeq ($(GPU),nvidia)
COMPOSE += -f docker-compose.nvidia.yml
endif
ifeq ($(GPU),amd)
COMPOSE += -f docker-compose.amd.yml
endif

.PHONY: up down logs pull test install build-source

up:            ## Start Ollama + Open WebUI (GPU=nvidia|amd for acceleration)
	$(COMPOSE) up -d

down:          ## Stop containers (models are kept in volumes)
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

pull:          ## Pull models listed in OLLAMA_MODELS
	./scripts/pull-models.sh

test:          ## Smoke-test the API
	./scripts/smoke-test.sh

install:       ## Native install (no Docker)
	./scripts/install.sh

build-source:  ## Build Ollama from source
	./scripts/build-from-source.sh
