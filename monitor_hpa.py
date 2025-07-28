#!/usr/bin/env python3
import subprocess
import time
import json
from datetime import datetime

def run_command(command):
    """Run a kubectl command and return the output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_hpa_status():
    """Get HPA status"""
    return run_command("kubectl get hpa provider-hpa -n blockchain-microservices -o wide")

def get_pod_count():
    """Get current provider pod count"""
    return run_command("kubectl get pods -n blockchain-microservices -l app=provider-service --no-headers | wc -l")

def get_pod_status():
    """Get detailed pod status"""
    return run_command("kubectl get pods -n blockchain-microservices -l app=provider-service")

def get_resource_usage():
    """Get resource usage for provider pods"""
    return run_command("kubectl top pods -n blockchain-microservices -l app=provider-service")

def monitor_hpa(duration=300, interval=5):
    """Monitor HPA and pods in real-time"""
    print("=" * 80)
    print("HPA MONITORING DASHBOARD")
    print("=" * 80)
    print(f"Monitoring started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration} seconds | Interval: {interval} seconds")
    print("=" * 80)
    
    start_time = time.time()
    iteration = 0
    
    while time.time() - start_time < duration:
        iteration += 1
        current_time = datetime.now().strftime('%H:%M:%S')
        
        print(f"\n[{current_time}] Iteration {iteration}")
        print("-" * 60)
        
        # Get HPA status
        print("HPA STATUS:")
        hpa_status = get_hpa_status()
        print(hpa_status)
        
        # Get pod count
        print(f"\nPOD COUNT:")
        pod_count = get_pod_count()
        print(f"Provider pods: {pod_count}")
        
        # Get pod status
        print(f"\nPOD STATUS:")
        pod_status = get_pod_status()
        print(pod_status)
        
        # Get resource usage
        print(f"\nRESOURCE USAGE:")
        resource_usage = get_resource_usage()
        print(resource_usage)
        
        print("-" * 60)
        
        # Wait for next iteration
        time.sleep(interval)
    
    print("=" * 80)
    print("Monitoring completed!")

if __name__ == "__main__":
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    monitor_hpa(duration=duration, interval=interval) 