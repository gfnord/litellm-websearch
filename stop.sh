#!/bin/bash
# Stop LiteLLM and Web Search Proxy services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping LiteLLM Proxy services...${NC}"

# Stop services
docker compose down

echo -e "${GREEN}Services stopped.${NC}"
echo ""
echo "Start services again with: ./start.sh"
