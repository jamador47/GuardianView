#!/bin/bash
# GuardianView - Automated Google Cloud Deployment Script
# This script deploys GuardianView to Google Cloud Run
# Requirements: gcloud CLI installed and authenticated

set -e

# === Configuration ===
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="guardianview"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🛡️  GuardianView - Cloud Deployment"
echo "===================================="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Step 1: Enable required APIs
echo "📡 Enabling required Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    containerregistry.googleapis.com \
    firestore.googleapis.com \
    --project="${PROJECT_ID}"

# Step 2: Build the container image
echo "🔨 Building container image..."
gcloud builds submit \
    --tag "${IMAGE_NAME}" \
    --project="${PROJECT_ID}"

# Step 3: Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},SAFETY_PROFILE=workshop" \
    --memory 1Gi \
    --cpu 1 \
    --timeout 3600 \
    --min-instances 0 \
    --max-instances 10 \
    --session-affinity

# Step 4: Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo ""
echo "✅ Deployment complete!"
echo "🌐 GuardianView is live at: ${SERVICE_URL}"
echo ""
echo "🛡️  Open the URL above to start using GuardianView."
echo "   Make sure to allow camera and microphone access."
