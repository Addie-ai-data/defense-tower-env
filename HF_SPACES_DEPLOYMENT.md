# Deploying Support Triage OpenEnv to Hugging Face Spaces

This guide walks you through deploying the Support Triage OpenEnv environment as a live Hugging Face Space.

## Prerequisites

- A Hugging Face account: [huggingface.co](https://huggingface.co)
- Git installed locally
- The support-triage-openenv repository cloned or accessible

## Step 1: Create a New Space

1. Go to [huggingface.co/new/spaces](https://huggingface.co/new/spaces)
2. Fill in the form:
   - **Space name**: e.g., `support-triage-openenv`
   - **License**: MIT
   - **SDK**: Select **Docker** (not Gradio or Streamlit)
   - **Docker port**: `8000`
   - **Visibility**: Public (recommended for competition/demo)
3. Click **Create Space**

HuggingFace will initialize an empty Docker Space repository.

## Step 2: Clone and Configure Your Space

```bash
# Clone your newly created Space
git clone https://huggingface.co/spaces/{YOUR_USERNAME}/{SPACE_NAME}
cd {SPACE_NAME}

# Verify the local git remote
git remote -v
# Should show: origin  https://huggingface.co/spaces/{YOUR_USERNAME}/{SPACE_NAME}
```

## Step 3: Copy Files from support-triage-openenv

Copy all project files into your Space repository:

```bash
# From within your {SPACE_NAME} directory
cp -r /path/to/tower_defense_env/Dockerfile .
cp -r /path/to/tower_defense_env/requirements.txt .
cp -r /path/to/tower_defense_env/.dockerignore .
cp -r /path/to/tower_defense_env/__init__.py .
cp -r /path/to/tower_defense_env/models.py .
cp -r /path/to/tower_defense_env/client.py .
cp -r /path/to/tower_defense_env/inference.py .
cp -r /path/to/tower_defense_env/openenv.yaml .
cp -r /path/to/tower_defense_env/pyproject.toml .
cp -r /path/to/tower_defense_env/README.md .
cp -r /path/to/tower_defense_env/server/ .

# If there's a .git directory in the source, you can do:
# cp -r /path/to/tower_defense_env/* .
```

## Step 4: Create / Update README

Ensure the Space README has proper metadata. Check that `README.md` starts with:

```yaml
---
title: Support Triage OpenEnv
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
license: mit
tags:
  - openenv
  - fastapi
  - customer-support
  - reinforcement-learning
python_version: "3.11"
---
```

This frontmatter instructs HuggingFace to:
- Use Docker SDK
- Expose port 8000
- Tag the Space appropriately

## Step 5: Push to HuggingFace

```bash
# Stage all files
git add .

# Commit
git commit -m "Initial Support Triage OpenEnv deployment"

# Push to main branch
git push origin main
```

HuggingFace will automatically:
1. Detect the Dockerfile
2. Build the Docker image
3. Start the container on port 8000
4. Make the Space live

**Note**: The first build may take 5-15 minutes. You can monitor progress in the Space's **Logs** tab.

## Step 6: Configure Environment Variables (Optional)

If you want to test with the LLM baseline agent:

1. Go to your Space page
2. Click **Settings** → **Space secrets**
3. Add these secrets:
   - **OPENAI_API_KEY**: Your OpenAI API key (required for LLM agent)
   - **MODEL_NAME**: `gpt-4o` (or another model)
   - **API_BASE_URL**: (optional, defaults to OpenAI production)

## Step 7: Test Your Space

Once the Space is live, you can test it:

### Via cURL

```bash
SPACE_URL="https://{username}-{space-name}.hf.space"

# Test endpoint is reachable
curl "$SPACE_URL/reset" -X POST

# Example: Reset an environment
curl "$SPACE_URL/reset" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"task_id": "support_easy"}'

# Example: Run a step
curl "$SPACE_URL/step" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"action_type": "select_ticket", "ticket_id": "BIL-1001"}'

# Get current state
curl "$SPACE_URL/state" -X GET
```

### Via Python

```python
import requests

SPACE_URL = "https://{username}-{space-name}.hf.space"

# Reset
response = requests.post(f"{SPACE_URL}/reset", json={"task_id": "support_easy"})
print(response.json())

# Step
action = {"action_type": "select_ticket", "ticket_id": "BIL-1001"}
response = requests.post(f"{SPACE_URL}/step", json=action)
print(response.json())

# State
response = requests.get(f"{SPACE_URL}/state")
print(response.json())
```

## Step 8: Run Baseline Evaluation

Once your Space is live and stable, you can run the baseline inference against it:

```bash
# Test with heuristic baseline (no API key needed)
python inference.py --agent heuristic

# Test with LLM baseline (requires OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
export MODEL_NAME=gpt-4o
export API_BASE_URL=https://{username}-{space-name}.hf.space
python inference.py --agent llm
```

## Troubleshooting

### Space Build Fails

**Check the Logs tab** in your Space for error messages. Common issues:

- **Docker build error**: Verify `Dockerfile` is in the root and `requirements.txt` is correct
- **Port binding error**: Ensure `app_port: 8000` in README metadata
- **Import errors**: Verify all Python files are present and `PYTHONPATH` is correct

**Solution**: You can edit files directly in the HF Space web editor and push fixes via git.

### Environment Not Reachable

- Wait a few minutes for the Space to fully start
- Check the Space **Runtime** to ensure it's running (green status)
- Verify DNS/network connectivity to `huggingface.co`

### LLM Baseline Script Fails

- Verify `OPENAI_API_KEY` is set: `echo $OPENAI_API_KEY`
- Check `MODEL_NAME` is valid (e.g., `gpt-4o`, `gpt-4o-mini`)
- If using custom `API_BASE_URL`, ensure it's reachable

## Making Updates

To update your Space after the initial deployment:

```bash
# Make changes locally
# Edit files, test locally with: uvicorn server.app:app --port 8000

# Push to HF
git add .
git commit -m "Update: <description of change>"
git push origin main
```

HuggingFace will automatically rebuild and redeploy.

## Appendix: Docker Image Info

The `Dockerfile` uses:
- **Base image**: `python:3.11-slim`
- **Workdir**: `/app`
- **Entrypoint**: `uvicorn server.app:app --host 0.0.0.0 --port 8000`
- **Python packages**: openenv-core, openai, fastapi, uvicorn, pydantic

The image is lightweight (~500MB) and should run comfortably on HF's standard hardware (2vCPU, 8GB RAM).

## Support

For HuggingFace Spaces documentation:
- [Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- [Docker Spaces Guide](https://huggingface.co/docs/hub/spaces-docker)
- [HF Community Forum](https://huggingface.co/discussions)

For OpenEnv issues:
- [OpenEnv Documentation](https://docs.openenv.xyz)
- [OpenEnv GitHub](https://github.com/openenv-foundation/openenv)
