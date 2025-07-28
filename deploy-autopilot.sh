#!/bin/bash

# GKE Autopilot Deployment Script for Blockchain Microservices

NAMESPACE="blockchain-microservices"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Blockchain Microservices GKE Autopilot Deployment ===${NC}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Not connected to a Kubernetes cluster.${NC}"
    echo -e "${YELLOW}Please run: gcloud container clusters get-credentials <cluster-name> --region=<region>${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"

# Create namespace
echo -e "${YELLOW}Creating namespace...${NC}"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests (excluding PersistentVolume)
echo -e "${YELLOW}Applying Kubernetes manifests...${NC}"

# Apply manifests
kubectl apply -f k8s-namespace.yaml
kubectl apply -f k8s-configmap.yaml
kubectl apply -f k8s-master-deployment.yaml
kubectl apply -f k8s-requester-deployment.yaml
kubectl apply -f k8s-provider-deployment.yaml
kubectl apply -f k8s-services.yaml

echo -e "${GREEN}✓ Kubernetes manifests applied${NC}"

# Wait for deployments to be ready
echo -e "${YELLOW}Waiting for deployments to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/master-deployment -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/requester-deployment -n $NAMESPACE
kubectl wait --for=condition=available --timeout=300s deployment/provider-deployment -n $NAMESPACE

echo -e "${GREEN}✓ All deployments are ready${NC}"

# Get service information
echo -e "${YELLOW}Getting service information...${NC}"
kubectl get services -n $NAMESPACE

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "${YELLOW}To access your services:${NC}"
echo -e "1. Get the external IP: kubectl get service provider-service -n $NAMESPACE"
echo -e "2. Access provider service: http://<EXTERNAL_IP>:5004"
echo -e "3. Check logs: kubectl logs -f deployment/master-deployment -n $NAMESPACE"
echo -e "4. Check pods: kubectl get pods -n $NAMESPACE"

# Show current status
echo -e "\n${YELLOW}Current deployment status:${NC}"
kubectl get deployments -n $NAMESPACE
echo -e "\n${YELLOW}Current pods:${NC}"
kubectl get pods -n $NAMESPACE 