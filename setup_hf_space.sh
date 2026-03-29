#!/bin/bash
# Setup script for Hugging Face Spaces deployment
# This script prepares and pushes the environment to HF Spaces

set -e

# Configuration
HF_USERNAME="Addie21"
SPACE_NAME="support-triage-openenv"
HF_SPACE_URL="https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}"

echo "=========================================="
echo "Hugging Face Spaces Deployment Script"
echo "=========================================="
echo ""
echo "HF Username: $HF_USERNAME"
echo "Space Name: $SPACE_NAME"
echo "Space URL: $HF_SPACE_URL"
echo ""

# Step 1: Create the Space (if it doesn't exist)
echo "[1/4] Creating Hugging Face Space..."
echo "Please create a new Space on https://huggingface.co/new/spaces with:"
echo "  - Space name: ${SPACE_NAME}"
echo "  - License: MIT"
echo "  - SDK: Docker"
echo "  - Docker port: 8000"
echo ""
echo "Press ENTER when you've created the Space..."
read -r

# Step 2: Clone the Space repo
echo "[2/4] Cloning Space repository..."
TEMP_DIR="/tmp/hf-space-${SPACE_NAME}"
rm -rf "$TEMP_DIR" 2>/dev/null || true
git clone "https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}" "$TEMP_DIR"
cd "$TEMP_DIR"

# Step 3: Copy files
echo "[3/4] Copying environment files..."
# Get the current directory (assuming this script is run from tower_defense_env)
SOURCE_DIR="$(pwd)"
cp -v "$SOURCE_DIR"/{README.md,Dockerfile,requirements.txt,.dockerignore,openenv.yaml,pyproject.toml} . || true
cp -v "$SOURCE_DIR"/{__init__.py,models.py,client.py,inference.py}.py . 2>/dev/null || true
cp -rv "$SOURCE_DIR"/server/ . || true
cp -v "$SOURCE_DIR"/{HF_SPACES_DEPLOYMENT.md,BASELINE_SCORE_ANALYSIS.md,SUBMISSION_CHECKLIST.md,validate_submission.py} . || true

# Step 4: Push to HF
echo "[4/4] Pushing to Hugging Face Spaces..."
git add .
git commit -m "Initial OpenEnv deployment: Support Triage Environment"
git push

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Your Space is being built at:"
echo "$HF_SPACE_URL"
echo ""
echo "Build may take 5-15 minutes. You can monitor progress in the Logs tab."
echo ""
echo "Once deployed, test with:"
echo "  curl -X POST $HF_SPACE_URL/reset"
