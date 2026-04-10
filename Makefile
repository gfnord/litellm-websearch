.PHONY: help build up down restart logs litellm-logs websearch-logs shell

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs from all services
	docker-compose logs -f

litellm-logs: ## Show logs from litellm service
	docker-compose logs -f litellm

websearch-logs: ## Show logs from websearch-proxy service
	docker-compose logs -f websearch-proxy

shell-litellm: ## Open shell in litellm container
	docker-compose exec litellm /bin/sh

shell-websearch: ## Open shell in websearch-proxy container
	docker-compose exec websearch-proxy /bin/sh

ps: ## Show running containers
	docker-compose ps
