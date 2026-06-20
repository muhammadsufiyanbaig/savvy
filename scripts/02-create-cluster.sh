#!/usr/bin/env bash
# Sprint 4 — Step 2: EKS cluster
# Run: bash scripts/02-create-cluster.sh
# Prereq: eksctl installed  (brew install eksctl)
#         kubectl installed (brew install kubectl)
# Takes ~20 minutes.
set -euo pipefail

echo "Creating EKS cluster from eksctl-cluster.yaml..."
echo "This takes ~20 minutes — do not interrupt."
echo ""

eksctl create cluster -f eksctl-cluster.yaml

echo ""
echo "Verifying cluster..."
kubectl get nodes
kubectl get namespaces

echo ""
echo "✅ Cluster ready."
echo "Next: run scripts/03-setup-databases.sh"
