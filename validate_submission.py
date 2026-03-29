#!/usr/bin/env python3
"""
Pre-Submission Validation Script for Support Triage OpenEnv

This script runs all required checks to ensure the environment is ready
for submission to the OpenEnv competition.

Run with: python validate_submission.py
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, List

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}{text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{GREEN}✅ {text}{RESET}")

def print_failure(text: str) -> None:
    """Print a failure message."""
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{CYAN}ℹ️  {text}{RESET}")

def run_command(cmd: str, description: str) -> Tuple[bool, str, str]:
    """Run a command and return success, stdout, stderr."""
    print_info(f"Running: {description}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def check_files_exist() -> bool:
    """Check that all required files exist."""
    print_header("1. FILE STRUCTURE CHECK")
    
    required_files = [
        "README.md",
        "openenv.yaml",
        "models.py",
        "inference.py",
        "requirements.txt",
        "Dockerfile",
        "server/app.py",
        "server/support_triage_environment.py",
    ]
    
    all_exist = True
    for file in required_files:
        path = Path(file)
        if path.exists():
            print_success(f"Found: {file}")
        else:
            print_failure(f"Missing: {file}")
            all_exist = False
    
    return all_exist

def check_dependencies() -> bool:
    """Check that required Python packages are installed."""
    print_header("2. DEPENDENCY CHECK")
    
    required_packages = [
        "openenv",
        "openai",
        "fastapi",
        "uvicorn",
        "pydantic",
    ]
    
    all_installed = True
    for package in required_packages:
        success, stdout, stderr = run_command(
            f"python -c 'import {package.split('[')[0]}'",
            f"Checking {package}..."
        )
        if success:
            print_success(f"Package available: {package}")
        else:
            print_failure(f"Package missing: {package}")
            all_installed = False
    
    return all_installed

def check_openenv_spec() -> bool:
    """Validate OpenEnv spec compliance."""
    print_header("3. OPENENV SPEC VALIDATION")
    
    success, stdout, stderr = run_command(
        "openenv validate .",
        "Running 'openenv validate'"
    )
    
    if success:
        print_success("OpenEnv spec is valid")
        print_info(stdout.strip())
        return True
    else:
        print_failure("OpenEnv validation failed")
        print(f"Error: {stderr}")
        return False

def check_baseline_inference() -> bool:
    """Test the baseline inference script."""
    print_header("4. BASELINE INFERENCE TEST")
    
    success, stdout, stderr = run_command(
        "python inference.py --agent heuristic",
        "Running baseline inference (heuristic agent)"
    )
    
    if success:
        print_success("Baseline inference executed successfully")
        
        # Try to parse the output as JSON
        try:
            import json
            output = json.loads(stdout)
            average_score = output.get("average_score", 0)
            num_tasks = len(output.get("results", []))
            print_info(f"Tasks completed: {num_tasks}")
            print_info(f"Average score: {average_score:.4f}")
            
            if num_tasks == 3:
                print_success("All 3 tasks executed")
            else:
                print_failure(f"Expected 3 tasks, got {num_tasks}")
                return False
            
            return True
        except json.JSONDecodeError:
            print_failure("Could not parse baseline output as JSON")
            print(stdout)
            return False
    else:
        print_failure("Baseline inference failed")
        print(f"Error: {stderr}")
        return False

def check_server_startup() -> bool:
    """Test that the FastAPI server can start."""
    print_header("5. SERVER STARTUP TEST")
    
    print_info("Starting server on port 8000 (will kill after 3 seconds)...")
    
    # Start server in background
    try:
        import subprocess
        import time
        
        proc = subprocess.Popen(
            ["python", "-m", "uvicorn", "server.app:app", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # Wait a bit for server to start
        time.sleep(2)
        
        # Check if process is still running
        if proc.poll() is None:
            print_success("Server started successfully")
            proc.terminate()
            proc.wait(timeout=5)
            print_success("Server shut down cleanly")
            return True
        else:
            stdout, stderr = proc.communicate()
            print_failure("Server failed to start")
            print(f"Error: {stderr}")
            return False
    except Exception as e:
        print_failure(f"Could not start server: {e}")
        return False

def check_dockerfile() -> bool:
    """Check Dockerfile syntax and structure."""
    print_header("6. DOCKERFILE CHECK")
    
    if not Path("Dockerfile").exists():
        print_failure("Dockerfile not found")
        return False
    
    with open("Dockerfile", "r") as f:
        content = f.read()
    
    checks = {
        "FROM": "Base image defined",
        "RUN pip install": "Dependencies installed",
        "EXPOSE 8000": "Port 8000 exposed",
        "CMD": "Entrypoint defined",
    }
    
    all_present = True
    for keyword, description in checks.items():
        if keyword in content:
            print_success(description)
        else:
            print_failure(f"Missing: {description}")
            all_present = False
    
    return all_present

def check_readme_content() -> bool:
    """Check README has required sections."""
    print_header("7. README CONTENT CHECK")
    
    if not Path("README.md").exists():
        print_failure("README.md not found")
        return False
    
    with open("README.md", "r") as f:
        content = f.read()
    
    sections = {
        "## Why This Is Useful": "Motivation section",
        "## Tasks": "Task definitions",
        "## Action Space": "Action space documentation",
        "## Observation Space": "Observation space documentation",
        "## Reward Design": "Reward function explanation",
        "## Baseline Inference": "Baseline script documentation",
        "## Reproducible Baseline Scores": "Baseline scores",
        "## Hugging Face Spaces": "HF Spaces deployment guide",
    }
    
    all_present = True
    for keyword, description in sections.items():
        if keyword in content:
            print_success(f"✓ {description}")
        else:
            print_failure(f"✗ {description}")
            all_present = False
    
    return all_present

def check_all() -> int:
    """Run all checks and return exit code."""
    print(f"\n{BOLD}{CYAN}Support Triage OpenEnv - Pre-Submission Validation{RESET}\n")
    
    results = []
    
    # Run all checks
    results.append(("File Structure", check_files_exist()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("OpenEnv Spec", check_openenv_spec()))
    results.append(("Baseline Inference", check_baseline_inference()))
    results.append(("Server Startup", check_server_startup()))
    results.append(("Dockerfile", check_dockerfile()))
    results.append(("README Content", check_readme_content()))
    
    # Summary
    print_header("VALIDATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{check_name:.<40} {status}")
    
    print(f"\n{BOLD}Result: {passed}/{total} checks passed{RESET}")
    
    if passed == total:
        print_success("All checks passed! Ready for submission. 🚀")
        return 0
    else:
        print_failure(f"{total - passed} check(s) failed. Please review above.")
        return 1

if __name__ == "__main__":
    sys.exit(check_all())
