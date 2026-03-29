@echo off
REM Hugging Face Spaces Deployment Script for Windows
REM Pushes Support Triage OpenEnv to HF Spaces

setlocal enabledelayedexpansion

set HF_USERNAME=Addie21
set SPACE_NAME=support-triage-openenv
set HF_SPACE_URL=https://huggingface.co/spaces/%HF_USERNAME%/%SPACE_NAME%

echo.
echo ============================================================
echo Hugging Face Spaces Deployment
echo ============================================================
echo HF Username: %HF_USERNAME%
echo Space Name: %SPACE_NAME%
echo Space URL: %HF_SPACE_URL%
echo ============================================================
echo.

REM Step 1: Verify prerequisites
echo [Step 1/4] Checking Prerequisites...
where git >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    exit /b 1
)
echo OK: Git found

REM Step 2: Verify HF Space exists
echo.
echo [Step 2/4] Verify HF Space Exists
echo.
echo Please create a new Space on:
echo   https://huggingface.co/new/spaces
echo.
echo Settings:
echo   - Space name: support-triage-openenv
echo   - License: MIT
echo   - SDK: Docker
echo   - Docker port: 8000
echo.
pause

REM Step 3: Clone and setup
echo.
echo [Step 3/4] Clone and Setup Space Repository...
set TEMP_DIR=%TEMP%\hf-space-%SPACE_NAME%
if exist "%TEMP_DIR%" (
    echo Removing existing temp directory...
    rmdir /s /q "%TEMP_DIR%" >nul 2>&1
)

set GIT_URL=https://huggingface.co/spaces/%HF_USERNAME%/%SPACE_NAME%
echo Cloning from: %GIT_URL%
git clone "%GIT_URL%" "%TEMP_DIR%"
if errorlevel 1 (
    echo ERROR: Failed to clone Space repository
    echo Please verify the Space exists at: %HF_SPACE_URL%
    exit /b 1
)

cd /d "%TEMP_DIR%"

REM Copy files
echo Copying files...
for %%F in (
    README.md
    Dockerfile
    requirements.txt
    .dockerignore
    openenv.yaml
    pyproject.toml
    __init__.py
    models.py
    client.py
    inference.py
    HF_SPACES_DEPLOYMENT.md
    BASELINE_SCORE_ANALYSIS.md
    SUBMISSION_CHECKLIST.md
    validate_submission.py
) do (
    if exist "%CD%\..\tower_defense_env\%%F" (
        copy "%CD%\..\tower_defense_env\%%F" . >nul
        echo   OK: %%F
    )
)

REM Copy server directory
echo Copying server directory...
if exist "%CD%\..\tower_defense_env\server" (
    if exist "server" rmdir /s /q "server"
    xcopy "%CD%\..\tower_defense_env\server" "server\" /e /i /q
    echo   OK: server/
)

REM Step 4: Push to HF
echo.
echo [Step 4/4] Push to Hugging Face...
git config user.email "ci@openenv.local"
git config user.name "OpenEnv Deployer"

git add .
git commit -m "Initial OpenEnv deployment: Support Triage Environment"
git push

if errorlevel 1 (
    echo.
    echo ERROR: Failed to push to Hugging Face Spaces
    echo.
    echo Make sure your HF token is configured:
    echo   1. Get a token from: https://huggingface.co/settings/tokens
    echo   2. Run: huggingface-cli login
    echo   3. Or set HF_TOKEN environment variable
    exit /b 1
)

REM Success
echo.
echo ============================================================
echo OK: Deployment Complete!
echo ============================================================
echo.
echo Your Space: %HF_SPACE_URL%
echo.
echo Docker image is being built (5-15 minutes)
echo Monitor progress in the Logs tab
echo.
echo Test with:
echo   curl -X POST %HF_SPACE_URL%/reset
echo   curl -X GET %HF_SPACE_URL%/state
echo.
echo ============================================================
echo.
pause
