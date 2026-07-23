# Deploy ProvePR single image to Cloud Run.
# Usage: .\scripts\deploy-cloud-run.ps1 -ProjectId "my-gcp-project" [-Region "us-central1"]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,
    [string]$Region = "us-central1",
    [string]$Service = "provepr",
    [string]$Repo = "provepr"
)

$ErrorActionPreference = "Stop"
$Image = "$Region-docker.pkg.dev/$ProjectId/$Repo/provepr:latest"

Write-Host "=== ProvePR Cloud Run deploy ==="
Write-Host "Project : $ProjectId"
Write-Host "Region  : $Region"
Write-Host "Image   : $Image"

gcloud config set project $ProjectId
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

$repoExists = $true
try {
    gcloud artifacts repositories describe $Repo --location=$Region | Out-Null
} catch {
    $repoExists = $false
}
if (-not $repoExists) {
    gcloud artifacts repositories create $Repo `
        --repository-format=docker `
        --location=$Region `
        --description="ProvePR images"
}

Write-Host "Building with Cloud Build (no local Docker required)..."
gcloud builds submit --tag $Image .

Write-Host "Deploying Cloud Run service..."
gcloud run deploy $Service `
    --image $Image `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --port 8080 `
    --memory 1Gi `
    --cpu 1 `
    --timeout 300 `
    --max-instances 3 `
    --set-env-vars "HERMES_ENABLE_PROJECT_PLUGINS=1,PROVEPR_HTTP_HOST=0.0.0.0"

Write-Host ""
Write-Host "IMPORTANT: Set secrets on the service (never bake into the image):"
Write-Host "  PROVEPR_TRIGGER_SECRET, GITHUB_TOKEN, JIRA_SERVER_URL, JIRA_EMAIL, JIRA_API_TOKEN, GOOGLE_API_KEY"
Write-Host "  Optional: SLACK_BOT_TOKEN, SLACK_DM_USER_ID, GEMINI_MODEL"
Write-Host "Example:"
Write-Host "  gcloud run services update $Service --region $Region --update-env-vars KEY=VALUE"
Write-Host ""
gcloud run services describe $Service --region $Region --format="value(status.url)"
