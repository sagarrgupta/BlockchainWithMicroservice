#!/usr/bin/env python3
import requests
import time
import threading
import random
from datetime import datetime

def make_request(provider_url, request_id):
    """Make a request to the provider service"""
    try:
        # Make a request to trigger some processing
        response = requests.get(f"{provider_url}/chain", timeout=5)
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Request {request_id}: Success")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Request {request_id}: Failed - {response.status_code}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Request {request_id}: Error - {e}")

def generate_load(provider_url, duration=300, requests_per_second=10):
    """Generate load for the specified duration"""
    print(f"Starting load generation...")
    print(f"Target: {provider_url}")
    print(f"Duration: {duration} seconds")
    print(f"Requests per second: {requests_per_second}")
    print("=" * 50)
    
    start_time = time.time()
    request_id = 0
    
    while time.time() - start_time < duration:
        # Create multiple threads to simulate concurrent load
        threads = []
        for i in range(requests_per_second):
            request_id += 1
            thread = threading.Thread(target=make_request, args=(provider_url, request_id))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Small delay to control rate
        time.sleep(1)
    
    print("=" * 50)
    print(f"Load generation completed. Total requests: {request_id}")

if __name__ == "__main__":
    # Get provider URL from command line or use default
    import sys
    provider_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5004"
    
    # Generate load for 5 minutes with 10 requests per second
    generate_load(provider_url, duration=300, requests_per_second=10) 