# Manual Hugging Face Spaces Deployment Guide

If you prefer to deploy manually or the automated scripts don't work, follow these steps.

## Prerequisites

1. Git installed and configured
2. Hugging Face account: https://huggingface.co
3. HuggingFace token with write access: https://huggingface.co/settings/tokens

## Step-by-Step Guide

### 1. Create a New Space on Hugging Face

1. Visit: https://huggingface.co/new/spaces
2. Fill in the form:
   - **Space name**: `support-triage-openenv` (or your choice)
   - **License**: MIT
   - **SDK**: Docker (important!)
   - **Docker port**: 8000
   - **Visibility**: Public
3. Click **Create Space**

HuggingFace will initialize an empty Docker Space repo.

### 2. Clone Your Space Locally

```bash
# Replace {your-username} with your actual HF username
git clone https://huggingface.co/spaces/{your-username}/support-triage-openenv
cd support-triage-openenv
```

### 3. Copy Files from support-triage-openenv

You need to copy all files from this repository to your Space:

```bash
# From your Space directory, get the files from the original repo
# Option A: If repos are in same parent directory:
cp -r ../tower_defense_env/{README.md,Dockerfile,requirements.txt,.dockerignore,openenv.yaml,pyproject.toml,__init__.py,models.py,client.py,inference.py,server,*.md,*.py} .

# Option B: If repos are in different locations:
cp /path/to/tower_defense_env/README.md .
cp /path/to/tower_defense_env/Dockerfile .
cp /path/to/tower_defense_env/requirements.txt .
cp /path/to/tower_defense_env/.dockerignore .
cp /path/to/tower_defense_env/openenv.yaml .
cp /path/to/tower_defense_env/pyproject.toml .
cp /path/to/tower_defense_env/__init__.py .
cp /path/to/tower_defense_env/models.py .
cp /path/to/tower_defense_env/client.py .
cp /path/to/tower_defense_env/inference.py .
cp -r /path/to/tower_defense_env/server .

# Copy documentation files
cp /path/to/tower_defense_env/HF_SPACES_DEPLOYMENT.md .
cp /path/to/tower_defense_env/BASELINE_SCORE_ANALYSIS.md .
cp /path/to/tower_defense_env/SUBMISSION_CHECKLIST.md .
cp /path/to/tower_defense_env/validate_submission.py .
```

### 4. Verify Files Are Correct

```bash
# Check structure
ls -la

# Verify Dockerfile exists
cat Dockerfile | head -5

# Verify app.py exists
cat server/app.py | head -5
```

Should see:
- `README.md` ✓
- `Dockerfile` ✓
- `requirements.txt` ✓
- `openenv.yaml` ✓
- `server/` directory ✓
- `models.py` ✓
- `inference.py` ✓

### 5. Commit and Push

```bash
# Add all files
git add .

# Check what will be committed
git status

# Commit
git commit -m "Initial OpenEnv deployment: Support Triage Environment"

# Push to HuggingFace
git push
```

If you get an authentication error, configure your HF token:

```bash
# Option 1: Using huggingface-cli
pip install huggingface-hub
huggingface-cli login
# Enter your token when prompted

# Option 2: Set environment variable (Linux/Mac)
export HF_TOKEN=hf_YourTokenHere
git push

# Option 2: Set environment variable (Windows PowerShell)
$env:HF_TOKEN = "hf_YourTokenHere"
git push

# Option 2: Set environment variable (Windows CMD)
set HF_TOKEN=hf_YourTokenHere
git push
```

### 6. Monitor the Build

Once pushed, HuggingFace will:
1. Detect the Dockerfile
2. Build the Docker image (5-15 minutes)
3. Start the container on port 8000
4. Make the Space live

Visit your Space page to monitor:
- Space URL: `https://huggingface.co/spaces/{your-username}/support-triage-openenv`
- Click the **Logs** tab to watch the Docker build

### 7. Configure Environment Variables (Optional)

To test with LLM baseline, add secrets in Space settings:

1. Go to your Space page
2. Click **Settings** → **Space secrets**
3. Add these secrets:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `MODEL_NAME`: `gpt-4o` or similar
   - `API_BASE_URL`: (optional)

### 8. Test Your Space

Once live, test the endpoints:

```bash
# Using curl
SPACE_URL="https://{your-username}-support-triage-openenv.hf.space"

# Reset environment
curl -X POST $SPACE_URL/reset

# Step with action
curl -X POST $SPACE_URL/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "select_ticket", "ticket_id": "BIL-1001"}'

# Get state
curl -X GET $SPACE_URL/state
```

Or using Python:

```python
import requests

SPACE_URL = "https://{your-username}-support-triage-openenv.hf.space"

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

## Troubleshooting

### Space Build Fails

1. **Check the Logs tab** for error messages
2. Common issues:
   - `Dockerfile` not in root directory
   - `requirements.txt` missing dependencies
   - Invalid `openenv.yaml` format

**Fix**: 
- Click **Settings** → **Health check** to restart
- Or delete and recreate the Space

### "File not found" Error

Make sure all files are copied and committed:

```bash
git status  # Should show nothing uncommitted
git log --oneline -3  # Should show your commit
```

### Authentication Error When Pushing

```bash
# Method 1: huggingface-cli
huggingface-cli login

# Method 2: Create a .git-credentials file (Linux/Mac)
git credential approve
protocol=https
host=huggingface.co
username=your-username
password=hf_YourTokenHere
^D

# Method 3: Use SSH keys (recommended for security)
# Generate SSH key and add to HF account settings
git remote set-url origin git@huggingface.co:spaces/{your-username}/support-triage-openenv.git
git push
```

### Space Building But Not Starting

Wait 5-10 minutes. Docker images can take time to build.

If it stays in "building", check **Settings** → **Space secrets** for correct environment variables.

### Environment Endpoints Return 404

1. Wait for Space to fully start (check Logs)
2. Verify the Space URL format: `https://{user}-{space-name}.hf.space`
3. Check that server is listening on port 8000 in Dockerfile

### LLM Baseline Fails

1. Verify `OPENAI_API_KEY` is set in Space secrets
2. Check `MODEL_NAME` is valid
3. Run with `--agent heuristic` if API fails:
   ```bash
   python inference.py --agent heuristic
   ```

## Success Indicators

✅ Space is live and responding:
```
curl https://{user}-{spacename}.hf.space/reset
→ Returns JSON response
```

✅ Baseline inference works:
```
python inference.py --agent heuristic
→ Completes with JSON summary
```

✅ All 3 tasks execute:
```
average_score: 0.8271
results: [easy, medium, hard]
```

---

**You're ready to submit!** 🚀
