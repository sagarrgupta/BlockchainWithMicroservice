## Project description
This repository implements a decentralized, microservices-based framework for disaster resource allocation using blockchain. Services (master, requester, provider, and JWT issuer) coordinate secure token issuance, request handling, and on-chain data persistence while scaling on Google Kubernetes Engine with shared Filestore-backed storage.

## Publication
- Citation: A. A. Khaleq and S. Gupta, "Decentralized Microservices-based Framework for Disaster Resource Allocation using Blockchain," 2025 3rd International Conference on Artificial Intelligence, Blockchain, and Internet of Things (AIBThings), Mt Pleasant, MI, USA, 2025, pp. 1-5, doi: 10.1109/AIBThings66987.2025.11296261. keywords: {Cloud computing;Scalability;Disasters;Microservice architectures;Real-time systems;Blockchains;Resource management;Time factors;Security;Internet of Things;blockchain;microservices;scalability;critical domain;real time systems;cloud},
- Paper link: https://ieeexplore.ieee.org/document/11296261

# Blockchain Microservices - Kubernetes Deployment
Complete deployment guide for blockchain microservices on Google Cloud Platform using Kubernetes.

## Prerequisites
- gcloud, kubectl, Docker
- GCP project with billing enabled
- Required APIs: container.googleapis.com, file.googleapis.com, compute.googleapis.com

## Quick Deployment

### 1. Setup Environment
```bash
gcloud auth login
gcloud config set project blockchain-with-microservice
gcloud services enable container.googleapis.com file.googleapis.com compute.googleapis.com
gcloud auth configure-docker

export PROJECT_ID=$(gcloud config get-value project --quiet)
export REGION=us-central1
export ZONE=us-central1-c
export REPO_ROOT=$(pwd)
```

### 2. Generate JWT Keys
```bash
python3 scripts/generate_jwt_keys.py
```

### 3. Create GKE Cluster
```bash
gcloud container clusters create blockchain-cluster \
  --region=$REGION --num-nodes=1 --machine-type=e2-standard-2 \
  --disk-size=20 --disk-type=pd-standard \
  --enable-autoscaling --min-nodes=1 --max-nodes=4
gcloud container clusters get-credentials blockchain-cluster --region=$REGION
```

### 4. Setup Filestore
```bash
gcloud filestore instances create blockchain-filestore \
  --zone=$ZONE --tier=STANDARD --file-share=name=vol1,capacity=1TB --network=name=default

FILESTORE_IP=$(gcloud filestore instances describe blockchain-filestore --zone=$ZONE --format='get(networks[0].ipAddresses[0])')
sed -i '' "s|^\([[:space:]]*server:[[:space:]]*\).*|\1${FILESTORE_IP}|" "k8s/k8s-filestore-pv-pvc.yaml"

kubectl create namespace blockchain-microservices --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/k8s-filestore-pv-pvc.yaml
```

### 5. Create Secrets
```bash
# Create JWT issuer keys secret
kubectl -n blockchain-microservices create secret generic jwt-issuer-key \
  --from-file=public.pem=keys/public.pem \
  --from-file=private.pem=keys/private.pem \
  --dry-run=client -o yaml | kubectl apply -f -

# Create API keys secret
export REAL_API_KEY=$(openssl rand -base64 32)
kubectl -n blockchain-microservices create secret generic node-api-keys \
  --from-literal=api-key-1="$REAL_API_KEY" \
  --from-literal=api-key-2="$REAL_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 6. Build and Push Images
```bash
docker build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/blockchain-master:latest -f Dockerfile .
docker build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/blockchain-requester:latest -f Dockerfile .
docker build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/blockchain-provider:latest -f Dockerfile .
docker build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/blockchain-jwt-issuer:latest -f Dockerfile .

docker push gcr.io/${PROJECT_ID}/blockchain-master:latest
docker push gcr.io/${PROJECT_ID}/blockchain-requester:latest
docker push gcr.io/${PROJECT_ID}/blockchain-provider:latest
docker push gcr.io/${PROJECT_ID}/blockchain-jwt-issuer:latest
```

### 7. Deploy Services and Autoscaling
```bash
# Apply all configurations
kubectl apply -f k8s/k8s-configmap.yaml
kubectl apply -f k8s/k8s-jwt-issuer-deployment.yaml
kubectl apply -f k8s/k8s-master-deployment.yaml
kubectl apply -f k8s/k8s-requester-deployment.yaml
kubectl apply -f k8s/k8s-provider-deployment.yaml
kubectl apply -f k8s/k8s-services.yaml

# Apply all HPA configurations
kubectl apply -f k8s/k8s-master-hpa.yaml
kubectl apply -f k8s/k8s-requester-hpa.yaml
kubectl apply -f k8s/k8s-provider-hpa.yaml
kubectl apply -f k8s/k8s-jwt-issuer-hpa.yaml
```

### 8. Initialize Database
```bash
PROVIDER_POD=$(kubectl get pods -l app=provider-service -n blockchain-microservices -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it -n blockchain-microservices "$PROVIDER_POD" -- python scripts/db_setup.py
```

### 9. Verify Deployment
```bash
# Check all pods are running
kubectl get pods -n blockchain-microservices

# Check services and get external IP
kubectl get svc provider-service -n blockchain-microservices

# Test the deployment (replace <EXTERNAL-IP> with actual IP)
curl -s http://<EXTERNAL-IP>:5004/city/1
```

## Key Commands

### Scaling
```bash
kubectl scale deployment master-deployment --replicas=3 -n blockchain-microservices
kubectl scale deployment requester-deployment --replicas=5 -n blockchain-microservices
kubectl scale deployment provider-deployment --replicas=3 -n blockchain-microservices
```

### Updates
```bash
# Rebuild and redeploy
docker build ... && docker push ...
kubectl rollout restart deployment/{master-deployment,requester-deployment,provider-deployment} -n blockchain-microservices

# Update config
kubectl apply -f k8s/k8s-configmap.yaml
kubectl rollout restart deployment/{master-deployment,requester-deployment,provider-deployment} -n blockchain-microservices
```

### Troubleshooting
```bash
kubectl logs -l app=provider-service -n blockchain-microservices --tail=100 -f
kubectl describe pod -l app=provider-service -n blockchain-microservices
kubectl get events -n blockchain-microservices
```

## Cleanup
```bash
kubectl delete namespace blockchain-microservices
gcloud filestore instances delete blockchain-filestore --zone=$ZONE --quiet
gcloud container clusters delete blockchain-cluster --region=$REGION --quiet
```

## Architecture

- **JWT Issuer**: Token authentication service
- **Master**: Blockchain coordination service  
- **Requester**: Client request handling
- **Provider**: Data storage and blockchain operations
- **Filestore**: Shared NFS storage for database
- **HPA**: Auto-scaling based on CPU/Memory usage (70% CPU, 80% Memory)

## Service Communication
- Internal: ClusterIP services (master, requester, jwt-issuer)
- External: LoadBalancer service (provider)
- Storage: PersistentVolume with Filestore NFS