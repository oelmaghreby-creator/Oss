# One-shot Ollama setup for Windows.
# Run in PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
# Optional:           -Models "qwen3:8b","gemma3:4b"   -SkipModels
param(
    [string[]]$Models = @("qwen3:8b", "qwen3:30b-a3b", "nomic-embed-text"),
    [switch]$SkipModels
)
$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Installing Ollama with winget..."
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
        # Pick up the new PATH entry without reopening the terminal.
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        Write-Host "winget not found. Download and run OllamaSetup.exe from https://ollama.com/download, then re-run this script."
        exit 1
    }
}

ollama --version

# The installer starts Ollama in the background; wait for the API to answer.
$ready = $false
for ($i = 0; $i -lt 30 -and -not $ready; $i++) {
    try { Invoke-RestMethod http://localhost:11434/api/version | Out-Null; $ready = $true }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) {
    Write-Host "Ollama is not responding. Start the Ollama app from the Start menu, then re-run this script."
    exit 1
}

if (-not $SkipModels) {
    foreach ($m in $Models) {
        Write-Host "Pulling $m..."
        ollama pull $m
    }
}

ollama list
Write-Host ""
Write-Host "Done. Try:  ollama run $($Models[0])"
Write-Host "Then, in another window, run 'ollama ps' to check how much of the model is on the GPU."
