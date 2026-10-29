# Starts Bordik for the local network and prints the address to open on a phone.
#
#   .\tools\lan-serve.ps1              # start on http://<lan-ip>:8000
#   .\tools\lan-serve.ps1 -Port 8080
#
# If the phone still cannot connect, run this once in an elevated PowerShell:
#   New-NetFirewallRule -DisplayName "Bordik $Port" -Direction Inbound `
#     -Protocol TCP -LocalPort $Port -Action Allow

param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$addresses = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -ExpandProperty IPAddress

if (-not $addresses) {
    $addresses = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" } |
        Select-Object -ExpandProperty IPAddress)
}

Write-Host "Bordik is starting on port $Port" -ForegroundColor Cyan
foreach ($address in $addresses) {
    Write-Host "  phone: http://$address`:$Port" -ForegroundColor Yellow
}
Write-Host "  health: http://$($addresses | Select-Object -First 1):$Port/health"
Write-Host "  diag:   http://$($addresses | Select-Object -First 1):$Port/diag"
Write-Host ""
Write-Host "Note: the phone must be on the same Wi-Fi, and the Windows firewall"
Write-Host "must allow inbound TCP $Port (see the comment at the top of this file)."
Write-Host ""

$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python -m uvicorn task_manager.main:app --host 0.0.0.0 --port $Port --reload
