#!/usr/bin/env bash
# Deploy ProvePR single image to Cloud Run.
# Usage: ./scripts/deploy-cloud-run.sh PROJECT_ID [REGION]
set -euo pipefail

PROJECT_ID="${1:?Usage: $0 PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"
SERVICE="provepr"
REPO="provepr"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/provepr:latest"

echo "=== ProvePR Cloud Run deploy ==="
echo "Project : ${PROJECT_ID}"
echo "Region  : ${REGION}"
echo "Image   : ${IMAGE}"

gcloud config set project "${PROJECT_ID}"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

if ! gcloud artifacts repositories describe "${REPO}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="ProvePR images"
fi

echo "Building with Cloud Build..."
gcloud builds submit --tag "${IMAGE}" .

echo "Deploying Cloud Run service (secrets must already be set or passed)..."
echo "If first deploy, set env vars in Console or re-run with --set-env-vars / --update-secrets."

gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 3 \
  --set-env-vars "HERMES_ENABLE_PROJECT_PLUGINS=1,PROVEPR_HTTP_HOST=0.0.0.0"

echo ""
echo "IMPORTANT: Set secrets on the service (do not bake into image):"
echo "  PROVEPR_TRIGGER_SECRET, GITHUB_TOKEN, JIRA_*, GOOGLE_API_KEY, Slack optional"
echo "Example:"
echo "  gcloud run services update ${SERVICE} --region ${REGION} --update-env-vars KEY=VALUE"
echo ""
gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)'
