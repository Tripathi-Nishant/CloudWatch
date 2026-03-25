# DriftWatch Frontend Deployment Script
# This script builds the React dashboard and syncs it to the S3 bucket.

param (
    [string]$BucketName = $env:S3_FRONTEND_BUCKET,
    [string]$Region = "ap-south-1"
)

if (-not $BucketName) {
    Write-Error "S3_FRONTEND_BUCKET environment variable or -BucketName parameter is required."
    exit 1
}

Write-Host "--- Starting Frontend Build ---" -ForegroundColor Cyan
Set-Location frontend
npm install
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed. Deployment aborted."
    exit 1
}

Write-Host "--- Syncing to S3: s3://$BucketName ---" -ForegroundColor Cyan
# Requires AWS CLI installed and configured
aws s3 sync dist/ s3://$BucketName --delete --region $Region

if ($LASTEXITCODE -ne 0) {
    Write-Error "S3 sync failed. Ensure AWS CLI is configured."
    exit 1
}

Write-Host "--- Deployment Successful! ---" -ForegroundColor Green
Write-Host "Your dashboard should be live at: http://$BucketName.s3-website-$Region.amazonaws.com"
Set-Location ..
