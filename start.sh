#!/usr/bin/env bash

set -e

START_TIME=$(date +%s)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
cd "$PROJECT_ROOT"

DC_BASE="docker compose"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    echo "Usage: ./start.sh [ENVIRONMENT] [FLAGS]"
    echo ""
    echo "Environments:"
    echo "  dev          Local development with hot-reload (default)"
    echo "  telemetry    Development with Grafana and Prometheus enabled"
    echo "  demo         Lightweight demo stack behind Nginx proxy"
    echo "  prod         Hardened production environment"
    echo "  test         Run unit and integration tests"
    echo "  load_test    Run locust container for load tests"
    echo "  lint         Run linters and static type checkers"
    echo ""
    echo "Flags:"
    echo "  --pull       Execute 'git pull' before assembling the stack"
    echo "  --clean      Execute 'down -v' to wipe database volumes before launch"
    echo "  -h, --help   Show this help message"
}

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

ENV=""
FLAG_PULL=false
FLAG_CLEAN=false

for arg in "$@"; do
    case "$arg" in
        -h|--help)
            show_help
            exit 0
            ;;
        --pull)
            FLAG_PULL=true
            ;;
        --clean)
            FLAG_CLEAN=true
            ;;
        *)
            if [ -z "$ENV" ]; then
                ENV="$arg"
            else
                echo -e "${RED}Error: Unknown argument '$arg'${NC}"
                show_help
                exit 1
            fi
            ;;
    esac
done

ENV="${ENV:-dev}"

if [ "$FLAG_PULL" = true ]; then
    echo -e "${BLUE}Syncing repository via git pull...${NC}"
    git pull
fi

COMPOSE_FILES=""

case "$ENV" in
    dev)
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"
        START_CMD="up -d --build"
        ;;
    telemetry)
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.telemetry.yml -f docker-compose.dev.yml -f docker-compose.telemetry.dev.yml"
        START_CMD="up -d --build"
        ;;
    demo)
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.demo.yml"
        START_CMD="up -d --build"
        ;;
    prod)
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.telemetry.yml -f docker-compose.demo.yml"
        START_CMD="up -d --build"
        ;;
    test)
        COMPOSE_FILES="-f docker-compose.test.yml"
        START_CMD="run --rm tests"
        ;;
    load_test)
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.load.yml"
        START_CMD="up -d --build"
        ;;
    lint)
        COMPOSE_FILES="-f docker-compose.test.yml"
        START_CMD="run --rm lint"
        ;;
    *)
        echo -e "${RED}Error: Unknown environment '$ENV'${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

if [ "$FLAG_CLEAN" = true ]; then
    echo -e "${BLUE}Cleaning environment: dropping containers and volumes...${NC}"
    $DC_BASE $COMPOSE_FILES down -v
else
    echo -e "${BLUE}Stopping active containers for target environment...${NC}"
    $DC_BASE $COMPOSE_FILES down
fi

echo -e "${GREEN}Launching target environment: [$ENV]...${NC}"
$DC_BASE $COMPOSE_FILES $START_CMD

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo -e "${GREEN}Execution finished successfully in ${DURATION}s.${NC}"
