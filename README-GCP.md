## GCP End-to-End Deployment (GKE + Filestore + HPA)

Easy, copy-paste runbook to deploy this system on Google Cloud. Targets macOS. Time: ~20–40 minutes. Costs: small GKE + Filestore (remember to Cleanup).

### What you’ll deploy
- JWT Issuer (issues tokens)
- Master, Requester, Provider services (Flask + blockchain node)
- Google Filestore (NFS) + PV/PVC for shared DB
- Kubernetes Services, ConfigMap, Secrets, and HPA for autoscaling

### Prerequisites
- gcloud, kubectl, Docker
- Billing enabled on your GCP project
- Logged in with sufficient permissions

```bash
gcloud auth login
gcloud config set project <YOUR_PROJECT_ID>
gcloud services enable container.googleapis.com file.googleapis.com compute.googleapis.com logging.googleapis.com monitoring.googleapis.com
gcloud auth configure-docker

export PROJECT_ID=$(gcloud config get-value project --quiet)
export REGION=us-central1
export ZONE=us-central1-c
export REPO_ROOT=/Users/sagargupta/BlockchainWithMicroservice
```

---

## Step 1. Generate RSA keys for JWT
- Option A (script):
```bash
python3 $REPO_ROOT/scripts/generate_jwt_keys.py
```
- Option B (OpenSSL):
```bash
mkdir -p $REPO_ROOT/keys
openssl genrsa -out $REPO_ROOT/keys/private.pem 2048
openssl rsa -in $REPO_ROOT/keys/private.pem -pubout -out $REPO_ROOT/keys/public.pem
```

## Step 2. Create secrets (where to put the keys)
- Recommended (no manual base64):
```bash
kubectl create namespace blockchain-microservices --dry-run=client -o yaml | kubectl apply -f -
kubectl -n blockchain-microservices create secret generic jwt-issuer-key \
  --from-file=public.pem=$REPO_ROOT/keys/public.pem \
  --from-file=private.pem=$REPO_ROOT/keys/private.pem \
  --dry-run=client -o yaml | kubectl apply -f -

export REAL_API_KEY=$(openssl rand -base64 32)

kubectl -n blockchain-microservices create secret generic node-api-keys \
  --from-literal=api-key-1="$REAL_API_KEY" \
  --from-literal=api-key-2="$REAL_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```
- Alternative (edit YAML): update base64 in `k8s/k8s-jwt-secrets.yaml`, then `kubectl apply -f` it.

## Step 3. Create the GKE cluster
```bash
gcloud container clusters create blockchain-cluster \
  --region=$REGION --num-nodes=1 --machine-type=e2-standard-2 \
  --disk-size=20 --disk-type=pd-standard \
  --enable-autoscaling --min-nodes=1 --max-nodes=1
gcloud container clusters get-credentials blockchain-cluster --region=$REGION
kubectl cluster-info && kubectl get nodes
```

## Step 4. Create Filestore and bind PV/PVC
Operator action: Ensure Filestore and GKE are in the same VPC and zone.
```bash
# you might need to change zone for this command, cluster zone is shown when you create your cluster
export ZONE=us-central1-c
gcloud filestore instances create blockchain-filestore \
  --zone=$ZONE --tier=STANDARD --file-share=name=vol1,capacity=1TB --network=name=default

FILESTORE_IP=$(gcloud filestore instances describe blockchain-filestore --zone=$ZONE --format='get(networks[0].ipAddresses[0])')
echo "Filestore IP: $FILESTORE_IP"

# this is used to change ip address of what filestore will use, you can update manually also by going into file
# Also go to repo root folder and run this first
export REPO_ROOT=$(pwd)
# check if file exists
ls $REPO_ROOT/k8s/k8s-filestore-pv-pvc.yaml

sed -i '' "s|^\([[:space:]]*server:[[:space:]]*\).*|\1${FILESTORE_IP}|" "$REPO_ROOT/k8s/k8s-filestore-pv-pvc.yaml"

kubectl create namespace blockchain-microservices --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f $REPO_ROOT/k8s/k8s-filestore-pv-pvc.yaml
kubectl wait --for=condition=Bound pvc/filestore-pvc -n blockchain-microservices --timeout=30s || true
kubectl get pv,pvc -n blockchain-microservices
```

If Filestore IP changes later, follow the “Update Flow” in `scripts/commands.py` (scale provider to 0 → delete PVC/PV → update `server:` → reapply → wait 30s → scale provider to 1).

## Step 5. Open docker and build and push images to GCR
```bash
export PROJECT_ID=$(gcloud config get-value project --quiet)
docker build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/blockchain-master:latest -f $REPO_ROOT/Dockerfile $REPO_ROOT
docker build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/blockchain-requester:latest -f $REPO_ROOT/Dockerfile $REPO_ROOT
docker build --platform linux/amd64 -t gcr.io/${PROJECT_ID}/blockchain-provider:latest -f $REPO_ROOT/Dockerfile $REPO_ROOT
docker push gcr.io/${PROJECT_ID}/blockchain-master:latest
docker push gcr.io/${PROJECT_ID}/blockchain-requester:latest
docker push gcr.io/${PROJECT_ID}/blockchain-provider:latest
```

## Step 6. Apply K8s config, deployments, and services
```bash
kubectl apply -f $REPO_ROOT/k8s/k8s-configmap.yaml
kubectl apply -f $REPO_ROOT/k8s/k8s-jwt-issuer-deployment.yaml
kubectl apply -f $REPO_ROOT/k8s/k8s-master-deployment.yaml
kubectl apply -f $REPO_ROOT/k8s/k8s-requester-deployment.yaml
kubectl apply -f $REPO_ROOT/k8s/k8s-provider-deployment.yaml
kubectl apply -f $REPO_ROOT/k8s/k8s-services.yaml
kubectl get pods -n blockchain-microservices -o wide
```

Tip: `blockchain-config` sets service names (e.g., `provider-service`) that the apps resolve via in-cluster DNS.

## Step 7. Create HPA (autoscaling)
```bash
kubectl apply -f $REPO_ROOT/k8s/k8s-requester-hpa.yaml
kubectl apply -f $REPO_ROOT/k8s/k8s-provider-hpa.yaml
kubectl get hpa -n blockchain-microservices -o wide
```

## Step 8. Scale all services to 1
```bash
kubectl scale deployment jwt-issuer-deployment --replicas=0 -n blockchain-microservices
kubectl scale deployment master-deployment --replicas=0 -n blockchain-microservices
kubectl scale deployment requester-deployment --replicas=0 -n blockchain-microservices
kubectl scale deployment provider-deployment --replicas=0 -n blockchain-microservices


kubectl scale deployment jwt-issuer-deployment --replicas=1 -n blockchain-microservices
kubectl scale deployment master-deployment --replicas=1 -n blockchain-microservices
kubectl scale deployment requester-deployment --replicas=1 -n blockchain-microservices
kubectl scale deployment provider-deployment --replicas=1 -n blockchain-microservices

kubectl get pods -n blockchain-microservices
```
<!-- if the above command shows all pods in containerCreating, check the issue by running
kubectl describe pod -n blockchain-microservices requester-deployment-84bbcbff7b-67brz
 -->

## Step 9. add database
```bash
PROVIDER_POD=$(kubectl get pods -l app=provider-service -n blockchain-microservices -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it -n blockchain-microservices "$PROVIDER_POD" -- python scripts/db_setup.py
```

## Step 9. Verify
- Provider external test (when EXTERNAL-IP is ready):
```bash
kubectl get svc provider-service -n blockchain-microservices
curl -s http://<EXTERNAL-IP>:5004/city/1
```
- Requester end-to-end test via port-forward:
```bash
kubectl port-forward service/requester-service -n blockchain-microservices 5003:5003 &
sleep 2
curl -s http://localhost:5003/request/1
```

---

## Day-2: Updates & operations
- Rotate keys:
```bash
kubectl -n blockchain-microservices create secret generic jwt-issuer-key \
  --from-file=public.pem=$REPO_ROOT/keys/public.pem \
  --from-file=private.pem=$REPO_ROOT/keys/private.pem \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/jwt-issuer-deployment -n blockchain-microservices
kubectl rollout restart deployment/{master-deployment,requester-deployment,provider-deployment} -n blockchain-microservices
```
- Update ConfigMap (service names, ports) and restart deployments:
```bash
kubectl apply -f $REPO_ROOT/k8s/k8s-configmap.yaml
kubectl rollout restart deployment/{master-deployment,requester-deployment,provider-deployment} -n blockchain-microservices
```
- Re-deploy latest images:
```bash
docker build ... && docker push ...
kubectl rollout restart deployment/{master-deployment,requester-deployment,provider-deployment} -n blockchain-microservices
```

## Troubleshooting (quick)
- Provider `ContainerCreating` with NFS timeouts:
  - Ensure same VPC/zone
  - Confirm PV `server:` is Filestore IP
  - Use Update Flow in `scripts/commands.py`
  - Inspect: `kubectl describe pod -l app=provider-service -n blockchain-microservices | sed -n '/Events:/,$p'`
- Image pull issues: `gcloud auth configure-docker`, rebuild/push, then `kubectl rollout restart ...`
- DNS issues: `kubectl run -it --rm --restart=Never netcheck --image=busybox -n blockchain-microservices -- nslookup provider-service`
- Logs: `kubectl logs -l app=provider-service -n blockchain-microservices --tail=100 -f`

## Cleanup (stop charges)
```bash
kubectl delete namespace blockchain-microservices || true
gcloud filestore instances delete blockchain-filestore --zone=$ZONE --quiet || true
gcloud container clusters delete blockchain-cluster --region=$REGION --quiet || true
```

Notes
- All waits use 30s timeouts for fast feedback.
- See `scripts/commands.py` for a full command list and the Filestore Update Flow.


