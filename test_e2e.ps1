param (
    [switch]$LaunchDashboard = $false
)

Write-Host "--- Chintu's Tech Adventures: E2E Integration Test ---" -ForegroundColor Cyan

# 1. VM Worker Health Check
$vmUrl = "http://34.100.185.201:5000"
Write-Host "`n[1/3] Checking GCP VM Worker Health ($vmUrl/health)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$vmUrl/health" -Method Get -TimeoutSec 10
    Write-Host "VM is reachable! Status:" -ForegroundColor Green
    $response | ConvertTo-Json -Compress | Write-Host
} catch {
    Write-Host "Error connecting to VM: $_" -ForegroundColor Red
    Write-Host "Please ensure the FastAPI server is running on the VM and port 5000 is open." -ForegroundColor Yellow
}

# 2. Episode Render Simulation Check
Write-Host "`n[2/3] Simulating Episode Render Hand-off Check..." -ForegroundColor Yellow
$RawVideo = "output\raw_notebooklm_video.mp4"

if (Test-Path $RawVideo) {
    Write-Host "Found local NotebookLM raw video asset at: $RawVideo" -ForegroundColor Green
    Write-Host "-> Ready for rendering! The orchestrator will send this to the VM." -ForegroundColor Green
} else {
    Write-Host "Warning: Local asset '$RawVideo' does not exist." -ForegroundColor Red
    Write-Host "Please place your pre-downloaded NotebookLM video asset in the 'output' folder and name it 'raw_notebooklm_video.mp4'." -ForegroundColor Yellow
    
    # Create the directory if it doesn't exist
    if (-Not (Test-Path "output")) {
        New-Item -ItemType Directory -Force -Path "output" | Out-Null
    }
}

Write-Host "`nTo test a full render without publishing to YouTube, you can run:" -ForegroundColor Cyan
Write-Host "python -m orchestrator run --topic `"Test Magic Breakfast Episode`" --no-publish" -ForegroundColor Cyan

# 3. Launching Streamlit Dashboard
Write-Host "`n[3/3] Dashboard UI..." -ForegroundColor Yellow
if ($LaunchDashboard) {
    Write-Host "Starting Streamlit Dashboard..." -ForegroundColor Green
    streamlit run dashboard/app.py
} else {
    Write-Host "To launch the Streamlit Dashboard, run:" -ForegroundColor Cyan
    Write-Host "streamlit run dashboard/app.py" -ForegroundColor Cyan
}

Write-Host "`nTesting complete." -ForegroundColor Cyan
