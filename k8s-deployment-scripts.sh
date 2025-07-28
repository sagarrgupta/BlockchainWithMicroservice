#!/bin/bash

# Kubernetes Deployment Scripts for Blockchain Microservices

PROJECT_ID="blockchain-with-microservice"
REGION="us-central1"
CLUSTER_NAME="blockchain-cluster"
NAMESPACE="blockchain-microservices"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Blockchain Microservices Kubernetes Deployment ===${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! command_exists gcloud; then
    echo -e "${RED}Error: gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

if ! command_exists kubectl; then
    echo -e "${RED}Error: kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${RED}Error: docker not found. Please install Docker.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"

# Authenticate with Google Cloud
echo -e "${YELLOW}Authenticating with Google Cloud...${NC}"
gcloud auth login
gcloud config set project $PROJECT_ID

# Configure Docker to use gcloud as a credential helper
echo -e "${YELLOW}Configuring Docker authentication...${NC}"
gcloud auth configure-docker

# Build and push Docker images
echo -e "${YELLOW}Building and pushing Docker images...${NC}"

# Build images
docker build -t gcr.io/$PROJECT_ID/blockchain-master:latest -f Dockerfile --target master .
docker build -t gcr.io/$PROJECT_ID/blockchain-requester:latest -f Dockerfile --target requester .
docker build -t gcr.io/$PROJECT_ID/blockchain-provider:latest -f Dockerfile --target provider .

# Push images
docker push gcr.io/$PROJECT_ID/blockchain-master:latest
docker push gcr.io/$PROJECT_ID/blockchain-requester:latest
docker push gcr.io/$PROJECT_ID/blockchain-provider:latest

echo -e "${GREEN}✓ Docker images built and pushed${NC}"

# Create GKE cluster if it doesn't exist
echo -e "${YELLOW}Setting up GKE cluster...${NC}"
if ! gcloud container clusters describe $CLUSTER_NAME --region=$REGION >/dev/null 2>&1; then
    echo -e "${YELLOW}Creating GKE cluster...${NC}"
    gcloud container clusters create $CLUSTER_NAME \
        --region=$REGION \
        --num-nodes=3 \
        --machine-type=e2-standard-2 \
        --enable-autoscaling \
        --min-nodes=1 \
        --max-nodes=10 \
        --enable-network-policy
else
    echo -e "${GREEN}✓ GKE cluster already exists${NC}"
fi

# Get credentials for the cluster
echo -e "${YELLOW}Getting cluster credentials...${NC}"
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION

# Create namespace
echo -e "${YELLOW}Creating namespace...${NC}"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests
echo -e "${YELLOW}Applying Kubernetes manifests...${NC}"

# Update image references in deployment files
sed -i "s/blockchain-with-microservice/$PROJECT_ID/g" k8s-*.yaml

# Apply manifests (excluding PersistentVolume for Autopilot compatibility)
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