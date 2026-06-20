#!/usr/bin/env bash
# Sprint 4 — Step 4: AWS Secrets Manager
# Run: bash scripts/04-setup-secrets.sh
# Edit ALL values in SECRETS section below before running.
# Get DB endpoints from 03-setup-databases.sh output.
set -euo pipefail

REGION="us-east-1"
DB_PASSWORD="CHANGE_ME_strong_password_123!"  # same as in 03-setup-databases.sh

# ── FILL THESE IN ─────────────────────────────────────────────────────────────
SECRET_KEY="$(openssl rand -hex 32)"          # auto-generated JWT secret
ANTHROPIC_API_KEY="sk-ant-CHANGE_ME"
AWS_ACCESS_KEY_ID_APP="CHANGE_ME"
AWS_SECRET_ACCESS_KEY_APP="CHANGE_ME"

# From 03-setup-databases.sh output:
USER_DB_HOST="savvy-user-db.CHANGE_ME.us-east-1.rds.amazonaws.com"
FINANCE_DB_HOST="savvy-finance-db.CHANGE_ME.us-east-1.rds.amazonaws.com"
BANK_DB_HOST="savvy-bank-db.CHANGE_ME.us-east-1.rds.amazonaws.com"
NOTIFICATION_DB_HOST="savvy-notification-db.CHANGE_ME.us-east-1.rds.amazonaws.com"
REDIS_HOST="savvy-redis.CHANGE_ME.cache.amazonaws.com"   # from 03-setup-databases.sh

SMTP_HOST="smtp.gmail.com"
SMTP_USERNAME="tools.sufiyan@gmail.com"
SMTP_PASSWORD="CHANGE_ME_gmail_app_password"

ONESIGNAL_APP_ID="CHANGE_ME"
ONESIGNAL_API_KEY="CHANGE_ME"
# ─────────────────────────────────────────────────────────────────────────────

SECRET_JSON=$(cat <<EOF
{
  "secret_key": "${SECRET_KEY}",
  "anthropic_api_key": "${ANTHROPIC_API_KEY}",
  "aws_access_key_id": "${AWS_ACCESS_KEY_ID_APP}",
  "aws_secret_access_key": "${AWS_SECRET_ACCESS_KEY_APP}",
  "s3_bucket": "savvy-bank-statements-prod",
  "db_url_user": "postgresql://user_service:${DB_PASSWORD}@${USER_DB_HOST}:5432/user_db",
  "db_url_finance": "postgresql://finance_service:${DB_PASSWORD}@${FINANCE_DB_HOST}:5432/finance_db",
  "db_url_bank": "postgresql://bank_service:${DB_PASSWORD}@${BANK_DB_HOST}:5432/bank_db",
  "db_url_notification": "postgresql://notification_service:${DB_PASSWORD}@${NOTIFICATION_DB_HOST}:5432/notification_db",
  "redis_base_url": "rediss://${REDIS_HOST}:6379",
  "smtp_host": "${SMTP_HOST}",
  "smtp_username": "${SMTP_USERNAME}",
  "smtp_password": "${SMTP_PASSWORD}",
  "onesignal_app_id": "${ONESIGNAL_APP_ID}",
  "onesignal_api_key": "${ONESIGNAL_API_KEY}"
}
EOF
)

echo "Creating secret savvy/production in Secrets Manager..."
aws secretsmanager create-secret \
  --name "savvy/production" \
  --description "Savvy production secrets" \
  --secret-string "$SECRET_JSON" \
  --region "$REGION" \
  2>/dev/null || \
aws secretsmanager put-secret-value \
  --secret-id "savvy/production" \
  --secret-string "$SECRET_JSON" \
  --region "$REGION"

echo ""
echo "SECRET_KEY generated: $SECRET_KEY"
echo "⚠  Save the SECRET_KEY above — needed if you ever rotate the secret manually."
echo ""
echo "✅ Secrets Manager step done."
echo "Next: run scripts/05-install-addons.sh"
