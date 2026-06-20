#!/usr/bin/env bash
# Sprint 4 — Step 1: IAM setup
# Run: bash scripts/01-setup-iam.sh
# Prereq: aws configure done (admin credentials)
set -euo pipefail

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: $ACCOUNT_ID"

# ── Deploy user (GitHub Actions) ─────────────────────────────────────────────
echo "Creating savvy-deploy IAM user..."
aws iam create-user --user-name savvy-deploy 2>/dev/null || echo "  user exists, skipping"

aws iam create-policy \
  --policy-name savvy-deploy-policy \
  --policy-document file://iam/deploy-user-policy.json \
  2>/dev/null || echo "  policy exists, skipping"

aws iam attach-user-policy \
  --user-name savvy-deploy \
  --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/savvy-deploy-policy"

# Create access key — save output; add to GitHub Secrets manually
echo "Creating access key for savvy-deploy..."
aws iam create-access-key --user-name savvy-deploy \
  | tee /tmp/savvy-deploy-keys.json
echo ""
echo "  ⚠  SAVE THESE KEYS → add to GitHub Secrets as:"
echo "     AWS_ACCESS_KEY_ID"
echo "     AWS_SECRET_ACCESS_KEY"
echo ""

# ── Secrets Manager read policy (for External Secrets Operator IRSA) ─────────
echo "Creating savvy-secrets-read policy..."
aws iam create-policy \
  --policy-name savvy-secrets-read \
  --policy-document file://iam/node-secrets-policy.json \
  2>/dev/null || echo "  policy exists, skipping"

# ── S3 bank statements policy ────────────────────────────────────────────────
echo "Creating savvy-s3-bank-statements policy..."
aws iam create-policy \
  --policy-name savvy-s3-bank-statements \
  --policy-document file://iam/s3-bank-statements-policy.json \
  2>/dev/null || echo "  policy exists, skipping"

echo ""
echo "✅ IAM step done."
echo "Next: run scripts/02-create-cluster.sh"
