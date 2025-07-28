# Blockchain Microservices - Kubernetes Deployment Guide

This guide provides step-by-step instructions for deploying the blockchain microservices project on Google Cloud Platform (GCP) using Kubernetes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GCP Setup](#gcp-setup)
3. [Code Modifications](#code-modifications)
4. [Deployment Steps](#deployment-steps)
5. [Scaling and Monitoring](#scaling-and-monitoring)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
- Google Cloud SDK (gcloud)
- kubectl
- Docker
- Git

### GCP Requirements
- Google Cloud Platform account
- Billing enabled
- Required APIs enabled:
  - Kubernetes Engine API
  - Container Registry API
  - Cloud Build API

## GCP Setup

### 1. Create GCP Project
```bash
# Create new project or use existing
gcloud projects create YOUR_PROJECT_ID --name="Blockchain Microservices"
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs
```bash
gcloud services enable container.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 3. Create GKE Cluster
```bash
gcloud container clusters create blockchain-cluster \
    --region=us-central1 \
    --num-nodes=3 \
    --machine-type=e2-standard-2 \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=10 \
    --enable-network-policy
```

### 4. Get Cluster Credentials
```bash
gcloud container clusters get-credentials blockchain-cluster --region=us-central1
```

## Code Modifications

### Key Changes Made

1. **Service Discovery**: Updated to use Kubernetes DNS service names
2. **Environment Variables**: Moved to Kubernetes ConfigMaps
3. **Health Checks**: Replaced Docker health checks with Kubernetes probes
4. **Storage**: Added PersistentVolume for database storage
5. **Networking**: Updated service communication patterns

### Files Modified

- `node.py`: Added Kubernetes service discovery functions
- `k8s-*.yaml`: Kubernetes manifests for all services
- `k8s-deployment-scripts.sh`: Automated deployment script
- `k8s-scaling-script.sh`: Service scaling script

## Deployment Steps

### 1. Prepare Environment
```bash
# Clone repository
git clone <your-repo-url>
cd BlockchainWithMicroservice

# Make scripts executable
chmod +x k8s-deployment-scripts.sh
chmod +x k8s-scaling-script.sh
```

### 2. Update Configuration
Edit `k8s-deployment-scripts.sh` and replace `YOUR_PROJECT_ID` with your actual GCP project ID.

### 3. Build and Deploy
```bash
# Run the deployment script
./k8s-deployment-scripts.sh
```

### 4. Verify Deployment
```bash
# Check namespace
kubectl get namespace blockchain-microservices

# Check deployments
kubectl get deployments -n blockchain-microservices

# Check services
kubectl get services -n blockchain-microservices

# Check pods
kubectl get pods -n blockchain-microservices
```

### 5. Access Services
```bash
# Get external IP for provider service
kubectl get service provider-service -n blockchain-microservices

# Access the service
curl http://<EXTERNAL_IP>:5004/chain
```

## Scaling and Monitoring

### Manual Scaling
```bash
# Scale master service to 3 replicas
kubectl scale deployment master-deployment --replicas=3 -n blockchain-microservices

# Scale all services
kubectl scale deployment master-deployment --replicas=3 -n blockchain-microservices
kubectl scale deployment requester-deployment --replicas=5 -n blockchain-microservices
kubectl scale deployment provider-deployment --replicas=3 -n blockchain-microservices
```

### Using Scaling Script
```bash
./k8s-scaling-script.sh
```

### Monitoring Setup
```bash
# Deploy monitoring stack
kubectl apply -f k8s-monitoring.yaml

# Access Prometheus
kubectl port-forward service/prometheus-service 9090:9090 -n blockchain-microservices

# Access Grafana
kubectl port-forward service/grafana-service 3000:3000 -n blockchain-microservices
```

## Service Communication

### Kubernetes Service Names
- Master Service: `master-service.blockchain-microservices.svc.cluster.local:5002`
- Requester Service: `requester-service.blockchain-microservices.svc.cluster.local:5003`
- Provider Service: `provider-service.blockchain-microservices.svc.cluster.local:5004`

### Internal Communication
Services communicate using Kubernetes DNS names:
```python
# Example: Requester calling Provider
provider_url = "http://provider-service.blockchain-microservices.svc.cluster.local:5004"
response = requests.get(f"{provider_url}/city/1")
```

## Key Differences from Docker Swarm

| Aspect | Docker Swarm | Kubernetes |
|--------|--------------|------------|
| Service Discovery | `service_name:port` | `service-name.namespace.svc.cluster.local:port` |
| Scaling | `docker service scale` | `kubectl scale deployment` |
| Health Checks | Docker healthcheck | Liveness/Readiness probes |
| Configuration | Environment variables | ConfigMaps/Secrets |
| Storage | Docker volumes | PersistentVolumes |
| Load Balancing | Built-in | Service types (ClusterIP/LoadBalancer) |

## Troubleshooting

### Common Issues

1. **Service Not Found**
   ```bash
   # Check if service exists
   kubectl get services -n blockchain-microservices
   
   # Check DNS resolution
   kubectl run test-dns --image=busybox --rm -it --restart=Never -- nslookup master-service
   ```

2. **Pod Not Starting**
   ```bash
   # Check pod status
   kubectl get pods -n blockchain-microservices
   
   # Check pod logs
   kubectl logs <pod-name> -n blockchain-microservices
   
   # Describe pod for details
   kubectl describe pod <pod-name> -n blockchain-microservices
   ```

3. **Database Issues**
   ```bash
   # Check persistent volume
   kubectl get pv,pvc -n blockchain-microservices
   
   # Check database setup
   kubectl exec -it <provider-pod> -n blockchain-microservices -- ls -la /data
   ```

### Useful Commands

```bash
# View all resources
kubectl get all -n blockchain-microservices

# Check events
kubectl get events -n blockchain-microservices

# Access pod shell
kubectl exec -it <pod-name> -n blockchain-microservices -- /bin/bash

# Port forward for debugging
kubectl port-forward service/master-service 5002:5002 -n blockchain-microservices
```

## Cost Optimization

### Resource Limits
- CPU: 250m-500m per pod
- Memory: 256Mi-512Mi per pod
- Use node autoscaling to minimize costs

### Scaling Strategy
- Start with 1 replica per service
- Scale based on actual load
- Use horizontal pod autoscaling for automatic scaling

## Security Considerations

1. **Network Policies**: Implement network policies to restrict pod-to-pod communication
2. **RBAC**: Use Role-Based Access Control for service accounts
3. **Secrets**: Store sensitive data in Kubernetes secrets
4. **TLS**: Enable TLS for service communication

## Next Steps

1. **Implement Horizontal Pod Autoscaler (HPA)**
2. **Add monitoring and alerting**
3. **Set up CI/CD pipeline**
4. **Implement backup and disaster recovery**
5. **Add security policies**

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Kubernetes logs
3. Check GCP Cloud Logging
4. Review service mesh options (Istio/Linkerd) for advanced networking 