#!/bin/bash
# Bash script to build and run the Tower Defense RL Docker container
# Usage: cd tower_defense_env && ./run_docker.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "Building Docker image 'tower-defense-env'..."
docker build -t tower-defense-env .

echo "Starting container (mapped 8000:8000)..."
docker run --rm -p 8000:8000 tower-defense-env &
CONTAINER_PID=$!

sleep 4

echo "Checking /health endpoint..."
if command -v curl >/dev/null 2>&1; then
  curl -f http://localhost:8000/health || echo "Health check failed."
else
  echo "curl not found; please check http://localhost:8000/health manually."
fi

echo "Container started with PID $CONTAINER_PID." 
echo "Press Ctrl+C to stop."
wait $CONTAINER_PID