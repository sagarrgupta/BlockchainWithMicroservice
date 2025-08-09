# To get the chain
curl http://localhost:5002/chain
curl http://localhost:5003/chain
curl http://localhost:5004/chain

# To get the nodes
curl http://localhost:5002/nodes
curl http://localhost:5003/nodes
curl http://localhost:5004/nodes

# To add a user
curl -X POST http://localhost:5002/add_user \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "name": "Sagar",
           "initial_balance": 100
         }'

# To add a user
curl -X POST http://localhost:5002/add_user \
     -H "Content-Type: application/json" \
     -d '{
           "id": 2,
           "name": "Mohit",
           "initial_balance": 200
         }'

# To transfer
curl -X POST http://localhost:5002/transfer \
     -H "Content-Type: application/json" \
     -d '{"from_id": 42, "to_id": 1, "amount": 2}'

# To get the balance
curl http://localhost:5004/request/1
curl http://localhost:5004/request/2

# To remove docker image
docker stop $(docker ps -q --filter "name=blockchainwithmicroservices") 2>/dev/null
docker rm   $(docker ps -a -q --filter "name=blockchainwithmicroservices") 2>/dev/null

# To start docker
docker-compose build --no-cache              
docker-compose up -d --remove-orphans

# To check the logs
docker compose logs -f provider_service

# To get into shell
docker exec -it blockchainwithmicroservice-requester_service-1 sh

# To send multiple requests
curl http://provider_service:5004/city/1
curl http://provider_service:5004/city/2
curl http://provider_service:5004/city/3

# To run more services
docker compose up --scale requester_service=3;
docker compose up --scale provider_service=3;
docker compose up --scale master_service=3;
docker compose up --scale master_service=3 --scale requester_service=5
# To get resource
curl http://127.0.0.1:5003/request/1

# To update resource
curl -X POST http://localhost:5003/update_resource/1/high

# To stop the docker
docker compose down

# To run the bootstrap node
docker exec -it 72bfc00ce90c50705155ef107544b311b084cc02f6b62186d6a3dfe3c8697d7e curl http://localhost:5003/request/1
docker exec -it cef5f69f68a2653ea14a76610fe0316ae43ac2a5f307101e7ed9cf4a97354a44 curl -X POST http://localhost:5003/update_resource/1/high

# To get the block propagation metrics
docker exec -it cef5f69f68a2653ea14a76610fe0316ae43ac2a5f307101e7ed9cf4a97354a44 curl http://localhost:5003/block_propagation_metrics
curl http://localhost:5004/block_propagation_metrics

docker exec -it cef5f69f68a2653ea14a76610fe0316ae43ac2a5f307101e7ed9cf4a97354a44 curl http://localhost:5003/chain
docker exec -it cef5f69f68a2653ea14a76610fe0316ae43ac2a5f307101e7ed9cf4a97354a44 curl http://localhost:5003/chain
docker exec -it cef5f69f68a2653ea14a76610fe0316ae43ac2a5f307101e7ed9cf4a97354a44 curl http://localhost:5002/chain
curl http://localhost:5004/chain

# To check docker version
docker exec -it cef5f69f68a2653ea14a76610fe0316ae43ac2a5f307101e7ed9cf4a97354a44 which docker

# time it takes
# without blockchain between 2 nodes: 7.05 ms
# without blockchain between 3 nodes: 4.64 ms
# without blockchain between 5 nodes: 7.30 ms
# without blockchain between 10 nodes: 13.278

# with 1 block (2 nodes): 16.88 ms
# with 2 blocks (2 nodes): 24.23 ms
# with 3 blocks (3 nodes): 72.73 ms
# with 5 blocks (5 nodes): 255.73.13 ms
# with 10 blocks (5 nodes): 2374.79 ms

# node1 = 2 chain - 5002
# node2 = 2 chain
# node3 = 1 chain -> register -> it passes longest chain -> copy local -> 2 chain

# shouldExternalUserCanChange = true/false
# /customChangeToDatabase 

"""

source venv/bin/activate
python src/intermediary.py 5004 127.0.0.1:5005

source venv/bin/activate
python src/intermediary.py 5005 127.0.0.1:5006

source venv/bin/activate
python src/intermediary.py 5006 127.0.0.1:5007

source venv/bin/activate
python src/intermediary.py 5007 127.0.0.1:5008

source venv/bin/activate
python src/intermediary.py 5008 127.0.0.1:5009

source venv/bin/activate
python src/intermediary.py 5009 127.0.0.1:5010

source venv/bin/activate
python src/intermediary.py 5010 127.0.0.1:5011

source venv/bin/activate
python src/intermediary.py 5011 127.0.0.1:5003

"""

docker swarm leave --force

docker swarm init

docker build -t blockchainwithmicroservice_db_setup_service -f Dockerfile .
docker build -t blockchainwithmicroservice_master_service -f Dockerfile .
docker build -t blockchainwithmicroservice_requester_service -f Dockerfile .
docker build -t blockchainwithmicroservice_provider_service -f Dockerfile .

docker stack deploy -c docker-compose.yml blockchain_stack

docker service scale blockchain_stack_master_service=3

curl http://master_service:5002/nodes
curl http://requester_service:5003/nodes
curl http://provider_service:5004/nodes

curl http://master_service:5002/chain
curl http://requester_service:5003/chain
curl http://provider_service:5004/chain

curl http://requester_service:5003/request/1

docker service scale blockchain_stack_master_service=3
docker service scale blockchain_stack_requester_service=3

# create cluster
gcloud container clusters create blockchain-cluster --region=us-central1 --num-nodes=1 --machine-type=e2-micro --disk-size=12 --disk-type=pd-standard

# get credentials
gcloud container clusters get-credentials blockchain-cluster --region=us-central1

# get cluster info
kubectl cluster-info

# =============================================================================
# KUBERNETES DEPLOYMENT COMMANDS (STEP BY STEP)
# =============================================================================

# Step 1: Delete old cluster (if needed)
gcloud container clusters delete blockchain-cluster --region=us-central1 --quiet

# Step 2: Create new cluster with larger nodes for Free Trial ($300 credits)
gcloud container clusters create blockchain-cluster --region=us-central1 --num-nodes=1 --machine-type=e2-standard-2 --disk-size=20 --disk-type=pd-standard --enable-autoscaling --min-nodes=1 --max-nodes=3

# Step 3: Get cluster credentials
gcloud container clusters get-credentials blockchain-cluster --region=us-central1

# Step 4: Verify cluster and check node resources
kubectl cluster-info
kubectl describe nodes

# Step 5: Configure Docker for Google Container Registry
gcloud auth configure-docker

# Step 6: Build Docker images with correct platform for Kubernetes
docker build --platform linux/amd64 -t gcr.io/blockchain-with-microservice/blockchain-master:latest .
docker build --platform linux/amd64 -t gcr.io/blockchain-with-microservice/blockchain-requester:latest .
docker build --platform linux/amd64 -t gcr.io/blockchain-with-microservice/blockchain-provider:latest .

# Step 7: Push images to Google Container Registry
docker push gcr.io/blockchain-with-microservice/blockchain-master:latest
docker push gcr.io/blockchain-with-microservice/blockchain-requester:latest
docker push gcr.io/blockchain-with-microservice/blockchain-provider:latest

# Step 8: Apply Kubernetes manifests
kubectl create namespace blockchain-microservices --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s-namespace.yaml
kubectl apply -f k8s-configmap.yaml
kubectl apply -f k8s-master-deployment.yaml
kubectl apply -f k8s-requester-deployment.yaml
kubectl apply -f k8s-provider-deployment.yaml
kubectl apply -f k8s-services.yaml

# Step 9: Check deployment status
kubectl get pods -n blockchain-microservices
kubectl get services -n blockchain-microservices

# Step 10: If pods are in ImagePullBackOff, restart deployments
kubectl rollout restart deployment/master-deployment -n blockchain-microservices
kubectl rollout restart deployment/requester-deployment -n blockchain-microservices
kubectl rollout restart deployment/provider-deployment -n blockchain-microservices

# Step 11: Wait for pods to be ready
kubectl get pods -n blockchain-microservices

# Step 12: Initialize database in provider pod
kubectl exec -it deployment/provider-deployment -n blockchain-microservices -- python scripts/db_setup.py

# Step 13: Test services
# Get external IP for provider service
kubectl get service provider-service -n blockchain-microservices

# Test provider service (external)
curl http://34.44.190.251:5004/city/1

# Port forward for requester service (internal)
kubectl port-forward service/master-service 5002:5002 -n blockchain-microservices
kubectl port-forward service/requester-service 5003:5003 -n blockchain-microservices
kubectl port-forward service/provider-service 5004:5004 -n blockchain-microservices

# Test requester service (in another terminal)
curl http://localhost:5003/request/1

# =============================================================================
# HORIZONTAL POD AUTOSCALER (HPA) COMMANDS
# =============================================================================

# Step 1: Create HPA for provider deployment
kubectl apply -f k8s/k8s-hpa.yaml

# Step 2: Create HPA for requester deployment
kubectl apply -f k8s/k8s-requester-hpa.yaml
kubectl apply -f k8s/k8s-provider-hpa.yaml

# Step 3: Check HPA status
kubectl get hpa -n blockchain-microservices -o wide
kubectl describe hpa provider-hpa -n blockchain-microservices
kubectl describe hpa requester-hpa -n blockchain-microservices

# Step 4: Monitor HPA events and scaling
kubectl get events -n blockchain-microservices --sort-by='.lastTimestamp' | grep -i hpa
kubectl get events -n blockchain-microservices --sort-by='.lastTimestamp' | grep -i scale

# Step 5: Check current pod counts and resource usage
kubectl get pods -n blockchain-microservices
kubectl top pods -n blockchain-microservices -l app=provider-service
kubectl top pods -n blockchain-microservices -l app=requester-service

# Step 6: Generate load for testing HPA (using curl)
# Test provider directly
for i in {1..50}; do echo "Request $i:"; curl -w "Response Time: %{time_total}s\n" -s http://34.44.190.251:5004/chain | grep -E "(length|Response Time)"; sleep 0.2; done

# Test requester (requires port forwarding)
kubectl port-forward service/requester-service 5003:5003 -n blockchain-microservices &
for i in {1..100}; do echo "Request $i:"; curl -w "Response Time: %{time_total}s\n" -s http://localhost:5003/request/1 | grep -E "(message|Response Time)"; sleep 0.1; done

# Step 7: Monitor scaling in real-time
# In one terminal:
watch -n 5 'kubectl get hpa -n blockchain-microservices -o wide && echo "---" && kubectl get pods -n blockchain-microservices'

# In another terminal:
watch -n 5 'kubectl top pods -n blockchain-microservices -l app=provider-service && echo "---" && kubectl top pods -n blockchain-microservices -l app=requester-service'

# Step 8: Check HPA configuration details
kubectl get hpa provider-hpa -n blockchain-microservices -o yaml
kubectl get hpa requester-hpa -n blockchain-microservices -o yaml

# Step 9: Monitor downscaling behavior
# After stopping load, monitor how long it takes to scale down
echo "Starting downscaling monitoring at $(date)" && for i in {1..20}; do echo "=== Check $i at $(date) ==="; kubectl get hpa -n blockchain-microservices -o wide; kubectl get pods -n blockchain-microservices --no-headers | wc -l; echo "---"; sleep 30; done

# Step 10: HPA Configuration Details
# Current HPA settings:
# - Scale Up: 30s stabilization window, 100% increase every 10s
# - Scale Down: 60s stabilization window, 10% decrease every 30s
# - CPU threshold: 10% for both services
# - Memory threshold: 20% for both services
# - Min replicas: 1, Max replicas: 5

# Step 11: Load testing scripts
# Create load_test_requester.py for comprehensive testing
# Create hpa_monitor.py for real-time monitoring
# Run load generation: python3 load_test_requester.py http://localhost:5003
# Run monitoring: python3 hpa_monitor.py 300 5

# Step 12: Successful HPA Test Results
# Provider HPA: Scaled from 1 to 3 pods when CPU exceeded 10%
# Requester HPA: Scaled from 1 to 2 pods when CPU exceeded 10%
# Response times remained consistent (~230ms) during scaling
# Load distribution worked correctly across multiple pods

# Step 13: Clean up HPA (if needed)
kubectl delete hpa provider-hpa -n blockchain-microservices
kubectl delete hpa requester-hpa -n blockchain-microservices

# =============================================================================
# USEFUL MONITORING COMMANDS
# =============================================================================

# Check pod logs
kubectl logs deployment/master-deployment -n blockchain-microservices
kubectl logs deployment/requester-deployment -n blockchain-microservices
kubectl logs deployment/provider-deployment -n blockchain-microservices

# Check pod status and details
kubectl describe pod -l app=master-service -n blockchain-microservices
kubectl describe pod -l app=requester-service -n blockchain-microservices
kubectl describe pod -l app=provider-service -n blockchain-microservices

# Check services
kubectl get services -n blockchain-microservices

# Check deployments
kubectl get deployments -n blockchain-microservices

# Check all resources
kubectl get all -n blockchain-microservices

# =============================================================================
# SCALING COMMANDS
# =============================================================================

# Scale services
kubectl scale deployment master-deployment --replicas=1 -n blockchain-microservices
kubectl scale deployment requester-deployment --replicas=1 -n blockchain-microservices
kubectl scale deployment provider-deployment --replicas=1 -n blockchain-microservices

kubectl scale deployment master-deployment --replicas=0 -n blockchain-microservices
kubectl scale deployment requester-deployment --replicas=0 -n blockchain-microservices
kubectl scale deployment provider-deployment --replicas=0 -n blockchain-microservices

# Check scaling status
kubectl get pods -n blockchain-microservices

# =============================================================================
# TROUBLESHOOTING COMMANDS
# =============================================================================

# Check pod logs
kubectl describe pod master-deployment- -n blockchain-microservices

# Check cluster events
kubectl get events -n blockchain-microservices

# Check node resources
kubectl describe nodes

# Check if images exist in registry
docker images | grep blockchain

# Test DNS resolution
kubectl run test-dns --image=busybox --rm -it --restart=Never -- nslookup master-service

# Access pod shell for debugging
kubectl exec -it deployment/provider-deployment -n blockchain-microservices -- /bin/bash

# =============================================================================
# CLEANUP COMMANDS
# =============================================================================

# Delete cluster (when done)
gcloud container clusters delete blockchain-cluster --region=us-central1 --quiet

# Delete namespace
kubectl delete namespace blockchain-microservices

# Remove Docker images
docker rmi gcr.io/blockchain-with-microservice/blockchain-master:latest
docker rmi gcr.io/blockchain-with-microservice/blockchain-requester:latest
docker rmi gcr.io/blockchain-with-microservice/blockchain-provider:latest

# =============================================================================
# SUCCESSFUL TEST RESULTS
# =============================================================================

# Provider service test (external IP: 34.44.190.251)
curl http://34.44.190.251:5004/city/1
# Response: {"blockTransactionData":{"recipient":"BackToSender","requestInfo":"/city/1","sender":"provider_provider-service:5004:provider-deployment-576fc46cdd-xqhb6"},"city_data":{"allocation_date":"2024-01-15","city_id":1,"city_name":"New York","disaster_risk_level":"High","resource_type":"Emergency Vehicles","resources_allocated":300}}

# Requester service test (port-forward required)
curl http://localhost:5003/request/1
# Response: {"city_data":{"allocation_date":"2024-01-15","city_id":1,"city_name":"New York","disaster_risk_level":"High","resource_type":"Emergency Vehicles","resources_allocated":300},"message":"Data fetched and time it took was 27.86 ms"}

# Blockchain chain test
curl http://34.44.190.251:5004/chain
# Response: {"chain":[{"index":1,"mined_by":"Genesis","previous_hash":"1","proof":100,"timestamp":1753688106.1688738,"transactions":[]}],"length":1}

# =============================================================================
# CLUSTER SPECIFICATIONS (SUCCESSFUL DEPLOYMENT)
# =============================================================================

# Cluster: blockchain-cluster
# Region: us-central1
# Nodes: 3 x e2-standard-2 (2 vCPU, 8GB RAM each)
# Cost: ~$0.30/hour = ~$7.20/day (Free Trial: $300 = ~41 days)
# Services: master-service (5002), requester-service (5003), provider-service (5004)
# Database: SQLite with 10 sample cities
# Status: All pods running, services healthy, blockchain syncing correctly

# =============================================================================
# GOOGLE FILESTORE (NFS) PERSISTENT VOLUME COMMANDS
# =============================================================================

# Step 1: Create Filestore instance in GCP Console
#   - Name: blockchain-filestore
#   - Fileshare name: vol1
#   - Region/Zone: (match your GKE nodes)
#   - Capacity: 1TB (minimum)
#   - Note the NFS IP address (e.g., 10.78.113.18)

# Step 2: Create PV and PVC YAML (k8s-filestore-pv-pvc.yaml)
#   - Use the NFS IP and export path (/vol1)

# Step 3: Apply PV and PVC
kubectl apply -f k8s-filestore-pv-pvc.yaml

# Step 4: Check PV and PVC status
kubectl get pv,pvc -n blockchain-microservices
kubectl describe pv filestore-pv
kubectl describe pvc filestore-pvc -n blockchain-microservices

# Step 5: Update provider deployment to use the PVC
#   (Already done in k8s-provider-deployment.yaml)

# Step 6: Redeploy provider deployment
kubectl apply -f k8s-provider-deployment.yaml

# Step 7: Initialize the database on the shared volume (run ONCE)
kubectl exec -it deployment/provider-deployment -n blockchain-microservices -- python scripts/db_setup.py

# Step 8: Verify all provider pods see the same database
kubectl get pods -n blockchain-microservices -l app=provider-service -o wide
kubectl exec -it <provider-pod-name> -n blockchain-microservices -- ls -l /data
kubectl exec -it <provider-pod-name> -n blockchain-microservices -- cat /data/disaster_resources.db | wc -c

# Step 9: Troubleshooting
# If PVC is Pending, ensure:
#   - storageClassName: "" is set in the PVC
#   - No selector field in the PVC
#   - PV and PVC accessModes and storage match
#   - PV and PVC are in the correct namespace
#   - Filestore and GKE nodes are in the same VPC and zone
#   - PV status is Bound, PVC status is Bound

# Step 10: Clean up (if needed)
kubectl delete pvc filestore-pvc -n blockchain-microservices
kubectl delete pv filestore-pv

# =============================================================================
# FULL CLEANUP: DELETE CLUSTER AND FILESTORE (STOP ALL CHARGES)
# =============================================================================

# Delete GKE cluster (replace region if needed)
gcloud container clusters delete blockchain-cluster --region=us-central1 --quiet

# Delete Filestore instance (replace zone and instance name as needed)
gcloud filestore instances delete blockchain-filestore --zone=us-central1-a --quiet

for pod in $(kubectl get pods -n blockchain-microservices -l app=master-service -o jsonpath='{.items[*].metadata.name}'); do
  echo "=== $pod ==="
  kubectl exec -it $pod -n blockchain-microservices -- curl -s http://localhost:5002/chain
  echo
done

for pod in $(kubectl get pods -n blockchain-microservices -l app=requester-service -o jsonpath='{.items[*].metadata.name}'); do
  echo "=== $pod ==="
  kubectl exec -it $pod -n blockchain-microservices -- curl -s http://localhost:5003/chain
  echo
done

for pod in $(kubectl get pods -n blockchain-microservices -l app=provider-service -o jsonpath='{.items[*].metadata.name}'); do
  echo "=== $pod ==="
  kubectl exec -it $pod -n blockchain-microservices -- curl -s http://localhost:5004/chain
  echo
done

# To deploy the latest changes
docker build --platform linux/amd64 -t gcr.io/blockchain-with-microservice/blockchain-master:latest . && docker build --platform linux/amd64 -t gcr.io/blockchain-with-microservice/blockchain-requester:latest . && docker build --platform linux/amd64 -t gcr.io/blockchain-with-microservice/blockchain-provider:latest . && docker push gcr.io/blockchain-with-microservice/blockchain-master:latest && docker push gcr.io/blockchain-with-microservice/blockchain-requester:latest && docker push gcr.io/blockchain-with-microservice/blockchain-provider:latest && kubectl rollout restart deployment/master-deployment -n blockchain-microservices && kubectl rollout restart deployment/requester-deployment -n blockchain-microservices && kubectl rollout restart deployment/provider-deployment -n blockchain-microservices && kubectl get pods -n blockchain-microservices

kubectl logs -f deployment/provider-deployment -n blockchain-microservices

kubectl get pods -n blockchain-microservices -l app=provider-service
kubectl logs -f provider-deployment-848444bbb6-79lph -n blockchain-microservices

kubectl get hpa -n blockchain-microservices -o wide

for i in {1..500}; do echo "Request $i:"; curl -w "Response Time: %{time_total}s\n" -s http://localhost:5003/request/1 | grep -E "(message|Response Time)"; sleep 0.05; done