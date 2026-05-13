#!/usr/bin/env bash
set -euo pipefail

# RealtyOps-OS GCP bootstrap for GitHub Actions staging deploy.
# Requires: gcloud, gh, authenticated gcloud and gh sessions.

REPO_DEFAULT="geetanshpardhi1/RealtyOps-OS"
PROJECT_ID_DEFAULT="realtyops-os-staging"
PROJECT_NAME_DEFAULT="RealtyOps OS Staging"
REGION_DEFAULT="asia-south1"
PUBSUB_TOPIC_DEFAULT="lead-events"
FIRESTORE_DB_DEFAULT="(default)"

REPO="${REPO:-$REPO_DEFAULT}"
PROJECT_ID="${PROJECT_ID:-$PROJECT_ID_DEFAULT}"
PROJECT_NAME="${PROJECT_NAME:-$PROJECT_NAME_DEFAULT}"
REGION="${REGION:-$REGION_DEFAULT}"
PUBSUB_TOPIC="${PUBSUB_TOPIC:-$PUBSUB_TOPIC_DEFAULT}"
FIRESTORE_DATABASE="${FIRESTORE_DATABASE:-$FIRESTORE_DB_DEFAULT}"
WIF_POOL_ID="${WIF_POOL_ID:-github-pool}"
WIF_PROVIDER_ID="${WIF_PROVIDER_ID:-github-provider}"
DEPLOYER_SA_NAME="${DEPLOYER_SA_NAME:-github-deployer}"
RUNTIME_SA_NAME="${RUNTIME_SA_NAME:-realtyops-runtime}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud not found. Install Google Cloud CLI first." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh not found. Install GitHub CLI first." >&2
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1 || true)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "No active gcloud account. Run: gcloud auth login" >&2
  exit 1
fi

echo "Active gcloud account: $ACTIVE_ACCOUNT"

# Ensure repo exists and gh auth works.
gh repo view "$REPO" >/dev/null

echo "Checking/creating project: $PROJECT_ID"
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud projects create "$PROJECT_ID" --name="$PROJECT_NAME"
fi

gcloud config set project "$PROJECT_ID" >/dev/null

# Attach billing account if missing.
BILLING_ENABLED="$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null || true)"
if [[ "$BILLING_ENABLED" != "True" ]]; then
  BILLING_ACCOUNT_ID="${BILLING_ACCOUNT_ID:-}"
  if [[ -z "$BILLING_ACCOUNT_ID" ]]; then
    BILLING_ACCOUNT_ID="$(gcloud billing accounts list --filter='open=true' --format='value(name)' | head -n1)"
  fi
  if [[ -z "$BILLING_ACCOUNT_ID" ]]; then
    echo "No open billing account found. Set BILLING_ACCOUNT_ID and retry." >&2
    exit 1
  fi
  echo "Linking billing account: $BILLING_ACCOUNT_ID"
  gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"
fi

echo "Enabling required APIs"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  serviceusage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com

echo "Creating Pub/Sub topic if missing: $PUBSUB_TOPIC"
gcloud pubsub topics describe "$PUBSUB_TOPIC" >/dev/null 2>&1 || gcloud pubsub topics create "$PUBSUB_TOPIC"

echo "Creating Firestore database if missing: $FIRESTORE_DATABASE"
if ! gcloud firestore databases describe --database="$FIRESTORE_DATABASE" >/dev/null 2>&1; then
  gcloud firestore databases create --database="$FIRESTORE_DATABASE" --location="$REGION" --type=firestore-native
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
POOL_NAME="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WIF_POOL_ID"
WIF_PROVIDER_RESOURCE="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WIF_POOL_ID/providers/$WIF_PROVIDER_ID"
DEPLOYER_SA_EMAIL="$DEPLOYER_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
RUNTIME_SA_EMAIL="$RUNTIME_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

echo "Creating service accounts"
gcloud iam service-accounts describe "$DEPLOYER_SA_EMAIL" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$DEPLOYER_SA_NAME" --display-name="GitHub Actions Deployer"

gcloud iam service-accounts describe "$RUNTIME_SA_EMAIL" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$RUNTIME_SA_NAME" --display-name="RealtyOps Runtime"

echo "Granting deployer roles"
for role in \
  roles/run.admin \
  roles/cloudbuild.builds.editor \
  roles/artifactregistry.admin \
  roles/storage.admin \
  roles/iam.serviceAccountUser
 do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$DEPLOYER_SA_EMAIL" \
    --role="$role" >/dev/null
 done

echo "Granting runtime roles"
for role in \
  roles/datastore.user \
  roles/pubsub.publisher \
  roles/logging.logWriter \
  roles/monitoring.metricWriter
 do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$RUNTIME_SA_EMAIL" \
    --role="$role" >/dev/null
 done

echo "Creating workload identity pool/provider"
gcloud iam workload-identity-pools describe "$WIF_POOL_ID" --location="global" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create "$WIF_POOL_ID" \
    --location="global" \
    --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER_ID" \
  --location="global" --workload-identity-pool="$WIF_POOL_ID" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER_ID" \
    --location="global" \
    --workload-identity-pool="$WIF_POOL_ID" \
    --display-name="GitHub OIDC Provider" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='$REPO'"

echo "Binding workload identity user for repo: $REPO"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/$POOL_NAME/attribute.repository/$REPO" >/dev/null

echo "Setting GitHub Actions repository secrets"
gh secret set GCP_PROJECT_ID --repo "$REPO" --body "$PROJECT_ID"
gh secret set GCP_REGION --repo "$REPO" --body "$REGION"
gh secret set PUBSUB_LEAD_EVENTS_TOPIC --repo "$REPO" --body "$PUBSUB_TOPIC"
gh secret set FIRESTORE_DATABASE --repo "$REPO" --body "$FIRESTORE_DATABASE"
gh secret set GCP_DEPLOYER_SA --repo "$REPO" --body "$DEPLOYER_SA_EMAIL"
gh secret set GCP_RUNTIME_SA --repo "$REPO" --body "$RUNTIME_SA_EMAIL"
gh secret set GCP_WIF_PROVIDER --repo "$REPO" --body "$WIF_PROVIDER_RESOURCE"

echo "Triggering staging workflow"
gh workflow run staging-deploy.yml --repo "$REPO"

echo "Done. Check workflow status with:"
echo "  gh run list --workflow=staging-deploy.yml --repo $REPO"
