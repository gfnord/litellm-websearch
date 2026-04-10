#!/bin/bash
# Start LiteLLM and Web Search Proxy services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting LiteLLM Proxy services...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found, creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env and set your SERPER_API_KEY${NC}"
fi

# Start services
echo "Starting Docker Compose services..."
docker compose up -d

# Wait for services to be healthy
echo -e "${GREEN}Waiting for services to start...${NC}"
sleep 3

# Show status
echo ""
echo -e "${GREEN}Service Status:${NC}"
docker compose ps

echo ""
echo -e "${GREEN}Services are running!${NC}"
echo ""
echo "LiteLLM Proxy:    http://localhost:4000"
echo "Web Search Proxy: http://localhost:4001"
echo ""
echo "View logs with: docker compose logs -f"
echo "Stop services with: ./stop.sh"
