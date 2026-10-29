# Checks why a phone can reach Bordik from the internet but not from the LAN.
#
#   .\tools\lan-check.ps1
#   .\tools\lan-check.ps1 -Port 8000 -PublicUrl https://tasks.example.com
#
# Run it ON THE SERVER (the machine that runs Bordik).

param(
    [int]$Port = 8000,
    [string]$PublicUrl = ""
)

$ErrorActionPreference = "Continue"

function Write-Title($text) {
    Write-Host ""
    Write-Host "== $text" -ForegroundColor Cyan
}

function Write-Result($ok, $text) {
    if ($ok) {
        Write-Host "  [ok]   $text" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $text" -ForegroundColor Red
    }
}

$addresses = @(Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -ExpandProperty IPAddress)

Write-Title "LAN addresses on this machine"
if ($addresses.Count -eq 0) {
    Write-Result $false "no LAN IPv4 address found (is the machine on a network?)"
} else {
    foreach ($address in $addresses) {
        Write-Host "  http://$address`:$Port"
    }
}

$lan = $addresses | Select-Object -First 1

Write-Title "Is the app listening on all interfaces?"
$listening = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
if ($listening.Count -eq 0) {
    Write-Result $false "nothing is listening on TCP $Port (start the app first)"
} else {
    $anyInterface = $listening | Where-Object { $_.LocalAddress -in @("0.0.0.0", "::") }
    if ($anyInterface) {
        Write-Result $true "listening on 0.0.0.0:$Port"
    } else {
        $bound = ($listening | Select-Object -ExpandProperty LocalAddress) -join ", "
        Write-Result $false "only bound to $bound - a phone cannot connect; use --host 0.0.0.0"
    }
}

Write-Title "Local health check (/health) on 127.0.0.1"
try {
    $local = Invoke-WebRequest "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 5
    Write-Result ($local.StatusCode -eq 200) "127.0.0.1:$Port/health -> $($local.StatusCode) $($local.Content)"
} catch {
    Write-Result $false "127.0.0.1:$Port/health failed: $($_.Exception.Message)"
}

if ($lan) {
    Write-Title "Self-check over the LAN address ($lan)"
    try {
        $viaLan = Invoke-WebRequest "http://$lan`:$Port/health" -UseBasicParsing -TimeoutSec 5
        Write-Result ($viaLan.StatusCode -eq 200) "http://$lan`:$Port/health -> $($viaLan.StatusCode)"
    } catch {
        Write-Result $false "http://$lan`:$Port/health failed from this machine: $($_.Exception.Message)"
    }

    Write-Title "Windows firewall rules for TCP $Port"
    $rules = @(Get-NetFirewallRule -Direction Inbound -Enabled True -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -match "Bordik|Docker|python|uvicorn" })
    if ($rules.Count -eq 0) {
        Write-Result $false "no matching inbound allow rule found"
        Write-Host "  fix (PowerShell as Administrator):"
        Write-Host "    New-NetFirewallRule -DisplayName `"Bordik $Port`" -Direction Inbound ``"
        Write-Host "      -Protocol TCP -LocalPort $Port -Action Allow" -ForegroundColor Yellow
    } else {
        foreach ($rule in $rules) {
            Write-Host "  $($rule.DisplayName) [$($rule.Action)]"
        }
    }
}

if ($PublicUrl) {
    Write-Title "Public URL from inside the LAN ($PublicUrl)"
    try {
        $public = Invoke-WebRequest "$($PublicUrl.TrimEnd('/'))/health" -UseBasicParsing -TimeoutSec 8
        Write-Result ($public.StatusCode -eq 200) "$PublicUrl/health -> $($public.StatusCode)"
    } catch {
        Write-Result $false "$PublicUrl/health failed from inside: $($_.Exception.Message)"
        Write-Host "  This is the usual case with NAT hairpin / loopback:" -ForegroundColor Yellow
        Write-Host "  many home routers cannot route your public address back into the LAN," -ForegroundColor Yellow
        Write-Host "  so the phone must use the LAN address above while it is on the same Wi-Fi." -ForegroundColor Yellow
    }
}

Write-Title "What to try on the phone (on the same Wi-Fi)"
if ($lan) {
    Write-Host "  1. http://$lan`:$Port/health"
    Write-Host "  2. http://$lan`:$Port/diag"
}
Write-Host "  If (1) times out from the phone but works here, the Wi-Fi likely uses"
Write-Host "  'AP/client isolation' (common on guest networks) - use a normal Wi-Fi"
Write-Host "  or wire the phone to the same subnet."
