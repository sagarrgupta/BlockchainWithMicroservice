#!/bin/bash

# Deploy JWT-based authentication components
# This script sets up the JWT issuer and updates the master with JWT verification

set -e

echo "Deploying JWT-based authentication components..."
echo "================================================"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace blockchain-microservices &> /dev/null; then
    echo "Creating namespace blockchain-microservices..."
    kubectl apply -f k8s-namespace.yaml
fi

# Generate RSA keys if they don't exist
if [ ! -f "private.pem" ] || [ ! -f "public.pem" ]; then
    echo "Generating RSA keypair for JWT authentication..."
    python3 generate_jwt_keys.py
    
    echo ""
    echo "IMPORTANT: Update k8s-jwt-secrets.yaml with the generated keys above"
    echo "Then run this script again to deploy the secrets."
    echo ""
    read -p "Press Enter after updating k8s-jwt-secrets.yaml..."
fi

# Deploy JWT secrets
echo "Deploying JWT secrets..."
kubectl apply -f k8s-jwt-secrets.yaml

# Deploy JWT issuer
echo "Deploying JWT issuer service..."
kubectl apply -f k8s-jwt-issuer-deployment.yaml

# Update master deployment with JWT verification
echo "Updating master deployment with JWT verification..."
kubectl apply -f k8s-master-deployment.yaml

# Wait for services to be ready
echo "Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/jwt-issuer-deployment -n blockchain-microservices
kubectl wait --for=condition=available --timeout=300s deployment/master-deployment -n blockchain-microservices

# Check service status
echo ""
echo "Service Status:"
echo "==============="
kubectl get pods -n blockchain-microservices -l app=jwt-issuer
kubectl get pods -n blockchain-microservices -l app=master-service
kubectl get services -n blockchain-microservices

echo ""
echo "JWT Authentication Components Deployed Successfully!"
echo "=================================================="
echo ""
echo "Services:"
echo "- JWT Issuer: jwt-issuer-service:8443"
echo "- Master (with JWT verification in node.py): master-service:5002"
echo ""
echo "To test the JWT flow:"
echo "1. kubectl exec -it <jwt-issuer-pod> -- python3 demo_jwt_flow.py"
echo "2. Or run demo_jwt_flow.py from within the cluster"
echo ""
echo "API Keys (for testing):"
echo "- ZXhhbXBsZS1hcGkta2V5LTEtMzItYnl0ZXMtYmFzZTY0LWVuY29kZWQ="
echo "- ZXhhbXBsZS1hcGkta2V5LTItMzItYnl0ZXMtYmFzZTY0LWVuY29kZWQ="
echo ""
echo "JWT Integration:"
echo "- JWT verification is integrated into node.py"
echo "- Authentication is MANDATORY for all protected operations"
echo "- Missing or invalid JWT tokens return 401 errors"
echo "- JWT scopes control access to different operations"
echo "- Public endpoints remain accessible without JWT"
echo ""
echo "Protected Endpoints:"
echo "- /nodes/register (POST) - blockchain:register scope"
echo "- /receive_block (POST) - blockchain:receive_block scope"
echo "- /mine (GET) - blockchain:mine scope"
echo "- /sync (GET) - blockchain:sync scope"
echo "- /block_propagation_metrics (GET) - blockchain:metrics scope" 