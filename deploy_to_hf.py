#!/usr/bin/env python3
"""
Hugging Face Spaces Deployment Script
Automatically pushes the Support Triage OpenEnv to HF Spaces
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

# Configuration
HF_USERNAME = "Addie21"
SPACE_NAME = "support-triage-openenv"
HF_SPACE_URL = f"https://huggingface.co/spaces/{HF_USERNAME}/{SPACE_NAME}"

def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"  Running: {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout: {description}")
        return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("Hugging Face Spaces Deployment")
    print("="*60)
    print(f"🤗 HF Username: {HF_USERNAME}")
    print(f"📦 Space Name: {SPACE_NAME}")
    print(f"🌐 Space URL: {HF_SPACE_URL}")
    print("="*60 + "\n")

    # Current directory should be tower_defense_env
    source_dir = Path.cwd()
    print(f"Source directory: {source_dir}")

    # Step 1: Verify HF Space exists
    print("\n[Step 1/4] Verify HF Space Exists")
    print(f"⚠️  Please create a new Space on:\n   https://huggingface.co/new/spaces")
    print("   with these settings:")
    print("   - Space name: support-triage-openenv")
    print("   - License: MIT")
    print("   - SDK: Docker")
    print("   - Docker port: 8000")
    print("\n✅ Press ENTER when you've created the Space...")
    input()

    # Step 2: Clone the Space repo
    print("\n[Step 2/4] Clone Space Repository")
    temp_dir = Path(temp_dir := source_dir.parent / f"hf-space-{SPACE_NAME}")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    git_url = f"https://huggingface.co/spaces/{HF_USERNAME}/{SPACE_NAME}"
    print(f"📥 Cloning from: {git_url}")
    if not run_command(f'git clone "{git_url}" "{temp_dir}"', "Clone HF Space"):
        print("❌ Failed to clone Space repository")
        print(f"   Make sure the Space exists at: {HF_SPACE_URL}")
        sys.exit(1)
    
    os.chdir(temp_dir)

    # Step 3: Copy files
    print("\n[Step 3/4] Copy Environment Files")
    files_to_copy = [
        "README.md",
        "Dockerfile",
        "requirements.txt",
        ".dockerignore",
        "openenv.yaml",
        "pyproject.toml",
        "__init__.py",
        "models.py",
        "client.py",
        "inference.py",
        "HF_SPACES_DEPLOYMENT.md",
        "BASELINE_SCORE_ANALYSIS.md",
        "SUBMISSION_CHECKLIST.md",
        "validate_submission.py",
    ]
    
    for file in files_to_copy:
        src = source_dir / file
        if src.exists():
            shutil.copy2(src, file)
            print(f"  ✓ {file}")
        else:
            print(f"  - {file} (not found)")
    
    # Copy server directory
    server_src = source_dir / "server"
    server_dst = Path("server")
    if server_src.exists() and server_src.is_dir():
        if server_dst.exists():
            shutil.rmtree(server_dst)
        shutil.copytree(server_src, server_dst)
        print(f"  ✓ server/ (directory)")

    # Step 4: Push to HF
    print("\n[Step 4/4] Push to Hugging Face")
    
    # Configure git (in case it's not configured globally)
    run_command('git config user.email "ci@openenv.local"', "Configure email")
    run_command('git config user.name "OpenEnv CI"', "Configure name")
    
    if not run_command("git add .", "Stage files"):
        print("❌ Failed to stage files")
        sys.exit(1)
    
    if not run_command(
        'git commit -m "Initial OpenEnv deployment: Support Triage Environment"',
        "Commit changes"
    ):
        print("❌ Failed to commit (files may already be synced)")
    
    if not run_command("git push", "Push to HF"):
        print("❌ Failed to push to HF Spaces")
        print("   Make sure your HF token is configured:")
        print("   - Set HF_TOKEN environment variable, or")
        print("   - Run: huggingface-cli login")
        sys.exit(1)

    # Done
    print("\n" + "="*60)
    print("✅ Deployment Complete!")
    print("="*60)
    print(f"\n🌐 Your Space: {HF_SPACE_URL}")
    print("\n📊 Build Status:")
    print("   Docker image is being built (5-15 minutes)")
    print("   Monitor progress in the Logs tab")
    print("\n🧪 Test Commands:")
    print(f"   curl -X POST {HF_SPACE_URL}/reset")
    print(f"   curl -X GET {HF_SPACE_URL}/state")
    print("\n📚 Documentation:")
    print("   - HF_SPACES_DEPLOYMENT.md")
    print("   - BASELINE_SCORE_ANALYSIS.md")
    print("   - SUBMISSION_CHECKLIST.md")
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
