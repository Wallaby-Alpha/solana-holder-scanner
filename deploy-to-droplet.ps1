<#
.SYNOPSIS
    Automated one-click deployment script from Windows to DigitalOcean Droplet.
.EXAMPLE
    .\deploy-to-droplet.ps1 -DropletIP "165.22.123.45"
    .\deploy-to-droplet.ps1 -DropletIP "165.22.123.45" -User "root"
#>

param(
    [Parameter(Mandatory = $true, HelpMessage = "Enter the Public IP address of your DigitalOcean Droplet")]
    [string]$DropletIP,

    [Parameter(Mandatory = $false)]
    [string]$User = "root"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Deploying Solana Alpha Tracker to DigitalOcean Droplet" -ForegroundColor Cyan
Write-Host " Target: $User@$DropletIP" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Test SSH connectivity
Write-Host "`n[1/4] Verifying SSH connectivity to $DropletIP..." -ForegroundColor Green
try {
    ssh -o ConnectTimeout=8 -o BatchMode=yes "$User@$DropletIP" "echo 'SSH Connection OK'" | Out-Null
    Write-Host "  SSH connectivity verified!" -ForegroundColor Green
} catch {
    Write-Host "  Warning: Direct non-interactive SSH test failed or requires host key verification." -ForegroundColor Yellow
    Write-Host "  Attempting standard connection..." -ForegroundColor Yellow
}

# 2. Create remote destination folder
Write-Host "`n[2/4] Preparing remote directory /opt/solana-holder-scanner..." -ForegroundColor Green
ssh "$User@$DropletIP" "mkdir -p /opt/solana-holder-scanner/data"

# 3. Transfer files via scp
Write-Host "`n[3/4] Uploading application files, models, and database..." -ForegroundColor Green
$sourceDir = $PSScriptRoot

# Transfer core files
scp -r "$sourceDir\backend" "$User@${DropletIP}:/opt/solana-holder-scanner/"
scp -r "$sourceDir\frontend" "$User@${DropletIP}:/opt/solana-holder-scanner/"
scp -r "$sourceDir\data" "$User@${DropletIP}:/opt/solana-holder-scanner/"
scp "$sourceDir\Dockerfile" "$User@${DropletIP}:/opt/solana-holder-scanner/"
scp "$sourceDir\docker-compose.yml" "$User@${DropletIP}:/opt/solana-holder-scanner/"
scp "$sourceDir\requirements.txt" "$User@${DropletIP}:/opt/solana-holder-scanner/"
scp "$sourceDir\solana-tracker.service" "$User@${DropletIP}:/opt/solana-holder-scanner/"
scp "$sourceDir\deploy.sh" "$User@${DropletIP}:/opt/solana-holder-scanner/"

Write-Host "  Files uploaded successfully!" -ForegroundColor Green

# 4. Execute deployment script on Droplet
Write-Host "`n[4/4] Starting 24/7 service on Droplet..." -ForegroundColor Green
ssh "$User@$DropletIP" "cd /opt/solana-holder-scanner && chmod +x deploy.sh && ./deploy.sh"

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host " Your Solana Holder Tracker is running 24/7 at:" -ForegroundColor Cyan
Write-Host " 👉 http://$DropletIP" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
