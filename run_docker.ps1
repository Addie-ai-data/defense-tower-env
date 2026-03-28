# PowerShell script to build and run the Tower Defense RL Docker container
# Usage: Open PowerShell, cd to project folder, then:
#   .\run_docker.ps1

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $projectDir

# Build container
Write-Host "Building Docker image 'tower-defense-env'..."
docker build -t tower-defense-env .

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker build failed. Please install Docker Desktop and ensure Docker is running."
    exit $LASTEXITCODE
}

# Run container
Write-Host "Starting container (mapped 8000:8000)..."
docker run --rm -p 8000:8000 tower-defense-env &

# Wait a few seconds for startup
Start-Sleep -Seconds 4

# Health check
Write-Host "Checking /health endpoint..."
try {
    $response = Invoke-RestMethod -Uri http://localhost:8000/health -TimeoutSec 10
    Write-Host "Health response:" $response
} catch {
    Write-Warning "Health check failed. Container may not be ready yet." 
}

Write-Host "To stop the container, use Ctrl+C if running in foreground or docker ps && docker stop <id>."