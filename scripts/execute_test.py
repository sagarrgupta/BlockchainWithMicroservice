#!/usr/bin/env python3

import requests
import time
import json
from datetime import datetime

def get_service_url(service_name, port):
    """Get the service URL based on service type"""
    if service_name == "provider-service":
        # Provider has LoadBalancer, get external IP
        import subprocess
        result = subprocess.run([
            "kubectl", "get", "service", "provider-service", 
            "-n", "blockchain-microservices", 
            "-o", "jsonpath='{.status.loadBalancer.ingress[0].ip}'"
        ], capture_output=True, text=True)
        external_ip = result.stdout.strip("'")
        return f"http://{external_ip}:{port}"
    else:
        # For ClusterIP services, port-forward or use internal DNS
        return f"http://{service_name}.blockchain-microservices.svc.cluster.local:{port}"

def make_request(service_url, city_id=1):
    """Make a request to the service and return timing data"""
    start_time = time.time()
    try:
        response = requests.get(f"{service_url}/request/{city_id}", timeout=10)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            # Extract the timing message
            message = data.get("message", "")
            # Parse the timing from message like "Data fetched and time it took was 123.45 ms"
            import re
            time_match = re.search(r'time it took was ([\d.]+) ms', message)
            total_time_ms = float(time_match.group(1)) if time_match else (end_time - start_time) * 1000
            
            return {
                "success": True,
                "total_time_ms": total_time_ms,
                "response_time_ms": (end_time - start_time) * 1000
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "total_time_ms": (end_time - start_time) * 1000
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time_ms": (time.time() - start_time) * 1000
        }

def get_block_propagation_metrics(service_url):
    """Get block propagation metrics from a service"""
    try:
        response = requests.get(f"{service_url}/block_propagation_metrics", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Error getting metrics from {service_url}: {e}")
        return None

def calculate_metrics(provider_metrics, requester_metrics, total_time_to_get_data):
    """Calculate the required metrics based on the test instructions"""
    if not provider_metrics or not requester_metrics:
        return None
    
    # Extract average values (they're already in milliseconds)
    start_time = 0
    chain_synced_time = provider_metrics.get("chainSyncedTime_avg", 0) - start_time
    block_mined_time = provider_metrics.get("blockMinedTime_avg", 0) - chain_synced_time
    block_propagation_time = provider_metrics.get("blockPropagationTime_avg", 0) - block_mined_time
    total_time = block_propagation_time - start_time + total_time_to_get_data
    
    return {
        "startTime": start_time,
        "chainSyncedTime": chain_synced_time,
        "blockMinedTime": block_mined_time,
        "blockPropagationTime": block_propagation_time,
        "totalTimeToGetData": total_time_to_get_data,
        "totalTime": total_time
    }

def main():
    print("Starting blockchain performance test...")
    print("=" * 50)
    
    # Service URLs
    requester_url = "http://requester-service.blockchain-microservices.svc.cluster.local:5003"
    provider_url = "http://provider-service.blockchain-microservices.svc.cluster.local:5004"
    
    # For external access, we need to port-forward or use LoadBalancer
    # Let's try port-forwarding for requester
    print("Setting up port forwarding for requester service...")
    import subprocess
    import threading
    
    # Start port-forward in background
    port_forward_process = subprocess.Popen([
        "kubectl", "port-forward", "service/requester-service", 
        "5003:5003", "-n", "blockchain-microservices"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait a moment for port-forward to establish
    time.sleep(3)
    
    try:
        requester_url = "http://localhost:5003"
        
        # Step 1: Make 5 requests and collect timing data
        print("Making 5 requests to /request endpoint...")
        request_times = []
        
        for i in range(5):
            print(f"Request {i+1}/5...")
            result = make_request(requester_url, city_id=1)
            if result["success"]:
                request_times.append(result["total_time_ms"])
                print(f"  Success: {result['total_time_ms']:.2f} ms")
            else:
                print(f"  Failed: {result['error']}")
            time.sleep(1)  # Small delay between requests
        
        if not request_times:
            print("No successful requests made. Exiting.")
            return
        
        # Calculate average total time to get data
        total_time_to_get_data = sum(request_times) / len(request_times)
        print(f"\nAverage total time to get data: {total_time_to_get_data:.2f} ms")
        
        # Step 2: Get block propagation metrics from both services
        print("\nCollecting block propagation metrics...")
        
        # For provider, use LoadBalancer external IP
        provider_external_ip = subprocess.run([
            "kubectl", "get", "service", "provider-service", 
            "-n", "blockchain-microservices", 
            "-o", "jsonpath='{.status.loadBalancer.ingress[0].ip}'"
        ], capture_output=True, text=True).stdout.strip("'")
        
        provider_url = f"http://{provider_external_ip}:5004"
        
        provider_metrics = get_block_propagation_metrics(provider_url)
        requester_metrics = get_block_propagation_metrics(requester_url)
        
        print(f"Provider metrics: {provider_metrics}")
        print(f"Requester metrics: {requester_metrics}")
        
        # Step 3: Calculate all metrics
        calculated_metrics = calculate_metrics(provider_metrics, requester_metrics, total_time_to_get_data)
        
        if calculated_metrics:
            # Step 4: Format results as table for Excel
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            table_data = {
                "Timestamp": timestamp,
                "Test Run": "Blockchain Performance Test",
                "startTime (ms)": calculated_metrics["startTime"],
                "chainSyncedTime (ms)": calculated_metrics["chainSyncedTime"],
                "blockMinedTime (ms)": calculated_metrics["blockMinedTime"],
                "blockPropagationTime (ms)": calculated_metrics["blockPropagationTime"],
                "totalTimeToGetData (ms)": calculated_metrics["totalTimeToGetData"],
                "totalTime (ms)": calculated_metrics["totalTime"],
                "Request Times (ms)": ", ".join([f"{t:.2f}" for t in request_times])
            }
            
            # Append to test file
            with open("scripts/test", "a") as f:
                f.write("\n\n" + "="*80 + "\n")
                f.write(f"TEST RESULTS - {timestamp}\n")
                f.write("="*80 + "\n")
                
                # Header row
                headers = list(table_data.keys())
                f.write("\t".join(headers) + "\n")
                
                # Data row
                values = [str(table_data[h]) for h in headers]
                f.write("\t".join(values) + "\n")
                
                f.write("\nDetailed Metrics:\n")
                f.write(f"Provider Metrics: {json.dumps(provider_metrics, indent=2)}\n")
                f.write(f"Requester Metrics: {json.dumps(requester_metrics, indent=2)}\n")
                f.write(f"Individual Request Times: {request_times}\n")
            
            print("\n" + "="*80)
            print("TEST COMPLETED SUCCESSFULLY!")
            print("="*80)
            print("Results appended to scripts/test file in Excel-compatible format.")
            print("\nTable Data:")
            for key, value in table_data.items():
                print(f"{key}: {value}")
            
        else:
            print("Failed to calculate metrics due to missing data.")
    
    finally:
        # Clean up port-forward
        port_forward_process.terminate()
        port_forward_process.wait()

if __name__ == "__main__":
    main()
