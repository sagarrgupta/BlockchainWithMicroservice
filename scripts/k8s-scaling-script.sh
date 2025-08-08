#!/bin/bash

# Kubernetes Scaling Script for Blockchain Microservices

NAMESPACE="blockchain-microservices"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Blockchain Microservices Scaling ===${NC}"

# Function to scale services
scale_service() {
    local service=$1
    local replicas=$2
    
    echo -e "${YELLOW}Scaling $service to $replicas replicas...${NC}"
    kubectl scale deployment $service-deployment --replicas=$replicas -n $NAMESPACE
    
    # Wait for scaling to complete
    kubectl rollout status deployment/$service-deployment -n $NAMESPACE
    
    echo -e "${GREEN}✓ $service scaled to $replicas replicas${NC}"
}

# Function to show current scaling
show_scaling() {
    echo -e "${YELLOW}Current deployment status:${NC}"
    kubectl get deployments -n $NAMESPACE
    echo -e "\n${YELLOW}Current pods:${NC}"
    kubectl get pods -n $NAMESPACE
}

# Function to show service endpoints
show_endpoints() {
    echo -e "${YELLOW}Service endpoints:${NC}"
    kubectl get services -n $NAMESPACE
}

# Main menu
while true; do
    echo -e "\n${GREEN}=== Scaling Menu ===${NC}"
    echo "1. Scale Master Service"
    echo "2. Scale Requester Service"
    echo "3. Scale Provider Service"
    echo "4. Scale All Services"
    echo "5. Show Current Status"
    echo "6. Show Service Endpoints"
    echo "7. Exit"
    
    read -p "Choose an option (1-7): " choice
    
    case $choice in
        1)
            read -p "Enter number of replicas for Master Service: " replicas
            scale_service "master" $replicas
            ;;
        2)
            read -p "Enter number of replicas for Requester Service: " replicas
            scale_service "requester" $replicas
            ;;
        3)
            read -p "Enter number of replicas for Provider Service: " replicas
            scale_service "provider" $replicas
            ;;
        4)
            read -p "Enter number of replicas for all services: " replicas
            scale_service "master" $replicas
            scale_service "requester" $replicas
            scale_service "provider" $replicas
            ;;
        5)
            show_scaling
            ;;
        6)
            show_endpoints
            ;;
        7)
            echo -e "${GREEN}Exiting...${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please choose 1-7.${NC}"
            ;;
    esac
done 