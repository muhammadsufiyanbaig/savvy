#!/usr/bin/env bash
# Sprint 4 — Step 3: RDS + ElastiCache + S3 + ACM + Route53
# Run: bash scripts/03-setup-databases.sh
# Edit the VARIABLES section below before running.
set -euo pipefail

# ── VARIABLES — edit these ────────────────────────────────────────────────────
REGION="us-east-1"
DOMAIN="savvy.app"                          # your domain
DB_PASSWORD="CHANGE_ME_strong_password_123!"  # same password all 4 RDS instances
VPC_ID=""          # fill after cluster creation: aws ec2 describe-vpcs --query "Vpcs[?Tags[?Key=='alpha.eksctl.io/cluster-name']].VpcId" --output text
SUBNET_IDS=""      # fill: aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[?MapPublicIpOnLaunch==\`false\`].SubnetId" --output text
# ─────────────────────────────────────────────────────────────────────────────

if [[ -z "$VPC_ID" || -z "$SUBNET_IDS" ]]; then
  echo "ERROR: Set VPC_ID and SUBNET_IDS in this script first."
  echo ""
  echo "  VPC_ID:"
  echo "    aws ec2 describe-vpcs --filters \"Name=tag:alpha.eksctl.io/cluster-name,Values=savvy-cluster\" --query 'Vpcs[0].VpcId' --output text"
  echo ""
  echo "  SUBNET_IDS (private, space-separated):"
  echo "    aws ec2 describe-subnets --filters \"Name=vpc-id,Values=<VPC_ID>\" \"Name=tag:aws-cdk:subnet-type,Values=Private\" --query 'Subnets[*].SubnetId' --output text"
  exit 1
fi

SUBNET_ARRAY=($SUBNET_IDS)

# ── RDS Subnet Group ──────────────────────────────────────────────────────────
echo "Creating RDS subnet group..."
aws rds create-db-subnet-group \
  --db-subnet-group-name savvy-db-subnet \
  --db-subnet-group-description "Savvy RDS subnet group" \
  --subnet-ids ${SUBNET_ARRAY[@]} \
  2>/dev/null || echo "  subnet group exists, skipping"

# Security group for RDS (allow from EKS nodes)
echo "Creating RDS security group..."
RDS_SG_ID=$(aws ec2 create-security-group \
  --group-name savvy-rds-sg \
  --description "Savvy RDS access from EKS" \
  --vpc-id "$VPC_ID" \
  --query GroupId --output text \
  2>/dev/null || \
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=savvy-rds-sg" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text)

# Allow PostgreSQL from within VPC
VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --query "Vpcs[0].CidrBlock" --output text)
aws ec2 authorize-security-group-ingress \
  --group-id "$RDS_SG_ID" \
  --protocol tcp --port 5432 \
  --cidr "$VPC_CIDR" \
  2>/dev/null || echo "  inbound rule exists"

echo "RDS SG: $RDS_SG_ID"

# ── Create 4 RDS instances ────────────────────────────────────────────────────
create_rds() {
  local IDENTIFIER=$1
  local DBNAME=$2
  local DBUSER=$3

  echo "Creating RDS: $IDENTIFIER..."
  aws rds create-db-instance \
    --db-instance-identifier "$IDENTIFIER" \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version "15.4" \
    --master-username "$DBUSER" \
    --master-user-password "$DB_PASSWORD" \
    --db-name "$DBNAME" \
    --allocated-storage 20 \
    --storage-type gp3 \
    --storage-encrypted \
    --db-subnet-group-name savvy-db-subnet \
    --vpc-security-group-ids "$RDS_SG_ID" \
    --no-publicly-accessible \
    --backup-retention-period 7 \
    --deletion-protection \
    --tags Key=project,Value=savvy Key=service,Value="$IDENTIFIER" \
    2>/dev/null || echo "  $IDENTIFIER exists, skipping"
}

create_rds "savvy-user-db"         "user_db"         "user_service"
create_rds "savvy-finance-db"      "finance_db"      "finance_service"
create_rds "savvy-bank-db"         "bank_db"         "bank_service"
create_rds "savvy-notification-db" "notification_db" "notification_service"

echo ""
echo "Waiting for RDS instances to become available (~10 minutes)..."
for ID in savvy-user-db savvy-finance-db savvy-bank-db savvy-notification-db; do
  echo "  waiting for $ID..."
  aws rds wait db-instance-available --db-instance-identifier "$ID"
  echo "  $ID ready"
done

# Print endpoints
echo ""
echo "RDS Endpoints (add to Secrets Manager as db_url_*):"
for ID in savvy-user-db savvy-finance-db savvy-bank-db savvy-notification-db; do
  EP=$(aws rds describe-db-instances --db-instance-identifier "$ID" \
    --query "DBInstances[0].Endpoint.Address" --output text)
  echo "  $ID → $EP"
done

# ── ElastiCache Redis ─────────────────────────────────────────────────────────
echo ""
echo "Creating ElastiCache subnet group..."
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name savvy-redis-subnet \
  --cache-subnet-group-description "Savvy Redis subnet" \
  --subnet-ids ${SUBNET_ARRAY[@]} \
  2>/dev/null || echo "  redis subnet group exists"

echo "Creating Redis security group..."
REDIS_SG_ID=$(aws ec2 create-security-group \
  --group-name savvy-redis-sg \
  --description "Savvy Redis access from EKS" \
  --vpc-id "$VPC_ID" \
  --query GroupId --output text \
  2>/dev/null || \
  aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=savvy-redis-sg" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$REDIS_SG_ID" \
  --protocol tcp --port 6379 \
  --cidr "$VPC_CIDR" \
  2>/dev/null || echo "  redis inbound rule exists"

echo "Creating ElastiCache Redis cluster..."
aws elasticache create-replication-group \
  --replication-group-id savvy-redis \
  --description "Savvy Redis cache + sessions" \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version "7.0" \
  --num-cache-clusters 1 \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --cache-subnet-group-name savvy-redis-subnet \
  --security-group-ids "$REDIS_SG_ID" \
  --tags Key=project,Value=savvy \
  2>/dev/null || echo "  redis exists, skipping"

echo "Waiting for Redis (~5 minutes)..."
aws elasticache wait replication-group-available --replication-group-id savvy-redis
REDIS_EP=$(aws elasticache describe-replication-groups \
  --replication-group-id savvy-redis \
  --query "ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address" --output text)
echo "Redis endpoint: $REDIS_EP"
echo "  redis_base_url = rediss://$REDIS_EP:6379"

# ── S3 Bucket ─────────────────────────────────────────────────────────────────
echo ""
echo "Creating S3 bucket: savvy-bank-statements-prod..."
aws s3api create-bucket \
  --bucket savvy-bank-statements-prod \
  --region "$REGION" \
  2>/dev/null || echo "  bucket exists, skipping"

aws s3api put-bucket-versioning \
  --bucket savvy-bank-statements-prod \
  --versioning-configuration Status=Enabled

aws s3api put-public-access-block \
  --bucket savvy-bank-statements-prod \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Lifecycle: delete non-current versions after 90 days
aws s3api put-bucket-lifecycle-configuration \
  --bucket savvy-bank-statements-prod \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "expire-old-versions",
      "Status": "Enabled",
      "Filter": {},
      "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
    }]
  }'

echo "S3 bucket ready: s3://savvy-bank-statements-prod"

# ── ACM Certificate ───────────────────────────────────────────────────────────
echo ""
echo "Requesting ACM certificate for *.$DOMAIN..."
CERT_ARN=$(aws acm request-certificate \
  --domain-name "$DOMAIN" \
  --subject-alternative-names "*.$DOMAIN" \
  --validation-method DNS \
  --region "$REGION" \
  --query CertificateArn --output text \
  2>/dev/null || \
  aws acm list-certificates \
    --query "CertificateSummaryList[?DomainName=='$DOMAIN'].CertificateArn | [0]" \
    --output text)

echo "Certificate ARN: $CERT_ARN"
echo ""
echo "⚠  Add the CNAME validation records from ACM to your DNS:"
aws acm describe-certificate --certificate-arn "$CERT_ARN" \
  --query "Certificate.DomainValidationOptions[*].{Domain:DomainName,Name:ResourceRecord.Name,Value:ResourceRecord.Value}" \
  --output table

# ── Route53 Hosted Zone ───────────────────────────────────────────────────────
echo ""
echo "Creating Route53 hosted zone for $DOMAIN..."
ZONE_ID=$(aws route53 create-hosted-zone \
  --name "$DOMAIN" \
  --caller-reference "savvy-$(date +%s)" \
  --query "HostedZone.Id" --output text \
  2>/dev/null | sed 's|/hostedzone/||' || \
  aws route53 list-hosted-zones-by-name \
    --dns-name "$DOMAIN" \
    --query "HostedZones[0].Id" --output text | sed 's|/hostedzone/||')

echo "Zone ID: $ZONE_ID"
echo ""
echo "⚠  Update your domain registrar nameservers to:"
aws route53 get-hosted-zone --id "$ZONE_ID" \
  --query "DelegationSet.NameServers" --output text

echo ""
echo "✅ Databases + Redis + S3 + ACM + Route53 step done."
echo "Next: run scripts/04-setup-secrets.sh"
