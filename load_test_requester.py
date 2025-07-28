#!/usr/bin/env python3
import requests
import time
import threading
import json
from datetime import datetime
import subprocess

def get_hpa_status():
    """Get current HPA status"""
    try:
        result = subprocess.run([
            "kubectl", "get", "hpa", "-n", "blockchain-microservices", "-o", "wide"
        ], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error getting HPA status: {e}"

def get_pod_count():
    """Get current pod counts for requester and provider"""
    try:
        requester_result = subprocess.run([
            "kubectl", "get", "pods", "-n", "blockchain-microservices", 
            "-l", "app=requester-service", "--no-headers"
        ], capture_output=True, text=True)
        provider_result = subprocess.run([
            "kubectl", "get", "pods", "-n", "blockchain-microservices", 
            "-l", "app=provider-service", "--no-headers"
        ], capture_output=True, text=True)
        
        requester_count = len(requester_result.stdout.strip().split('\n')) if requester_result.stdout.strip() else 0
        provider_count = len(provider_result.stdout.strip().split('\n')) if provider_result.stdout.strip() else 0
        
        return requester_count, provider_count
    except Exception as e:
        return 0, 0

def make_request(requester_url, request_id):
    """Make a request to the requester service and log response time"""
    start_time = time.time()
    try:
        response = requests.get(f"{requester_url}/request/1", timeout=30)
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Request {request_id:3d}: SUCCESS | Response Time: {response_time:6.1f}ms | Status: {response.status_code} | Response: {json.dumps(response_data, indent=2)}")
            except:
                print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Request {request_id:3d}: SUCCESS | Response Time: {response_time:6.1f}ms | Status: {response.status_code} | Response: {response.text[:100]}...")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Request {request_id:3d}: FAILED  | Response Time: {response_time:6.1f}ms | Status: {response.status_code} | Response: {response.text[:100]}...")
        
        return response_time
    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Request {request_id:3d}: ERROR   | Response Time: {response_time:6.1f}ms | Error: {e}")
        return response_time

def generate_load(requester_url, duration=300, requests_per_second=5):
    """Generate load for the specified duration"""
    print("=" * 100)
    print("LOAD TESTING DASHBOARD")
    print("=" * 100)
    print(f"Target: {requester_url}/request/1")
    print(f"Duration: {duration} seconds")
    print(f"Requests per second: {requests_per_second}")
    print(f"Total expected requests: {duration * requests_per_second}")
    print("=" * 100)
    
    start_time = time.time()
    request_id = 0
    response_times = []
    
    # Get initial pod counts
    initial_requester_count, initial_provider_count = get_pod_count()
    print(f"\nInitial Pod Counts - Requester: {initial_requester_count}, Provider: {initial_provider_count}")
    print("Initial HPA Status:")
    print(get_hpa_status())
    print("\n" + "=" * 100)
    print("STARTING LOAD GENERATION...")
    print("=" * 100)
    
    while time.time() - start_time < duration:
        # Create multiple threads to simulate concurrent load
        threads = []
        thread_response_times = []
        
        for i in range(requests_per_second):
            request_id += 1
            thread = threading.Thread(target=lambda r_id=request_id: thread_response_times.append(make_request(requester_url, r_id)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect response times
        response_times.extend(thread_response_times)
        
        # Print summary every 10 seconds
        if request_id % (requests_per_second * 10) == 0:
            current_requester_count, current_provider_count = get_pod_count()
            avg_response_time = sum(response_times[-requests_per_second*10:]) / len(response_times[-requests_per_second*10:]) if response_times else 0
            max_response_time = max(response_times[-requests_per_second*10:]) if response_times else 0
            min_response_time = min(response_times[-requests_per_second*10:]) if response_times else 0
            
            print(f"\n{'='*60}")
            print(f"SUMMARY at {datetime.now().strftime('%H:%M:%S')} - Request #{request_id}")
            print(f"Pod Counts - Requester: {current_requester_count} (was {initial_requester_count}), Provider: {current_provider_count} (was {initial_provider_count})")
            print(f"Response Times - Avg: {avg_response_time:.1f}ms, Min: {min_response_time:.1f}ms, Max: {max_response_time:.1f}ms")
            print(f"Current HPA Status:")
            print(get_hpa_status())
            print(f"{'='*60}\n")
        
        # Small delay to control rate
        time.sleep(1)
    
    # Final summary
    print("=" * 100)
    print("LOAD TESTING COMPLETED")
    print("=" * 100)
    print(f"Total requests: {request_id}")
    print(f"Total response times collected: {len(response_times)}")
    
    if response_times:
        print(f"Response Time Statistics:")
        print(f"  Average: {sum(response_times) / len(response_times):.1f}ms")
        print(f"  Minimum: {min(response_times):.1f}ms")
        print(f"  Maximum: {max(response_times):.1f}ms")
        print(f"  Median: {sorted(response_times)[len(response_times)//2]:.1f}ms")
    
    final_requester_count, final_provider_count = get_pod_count()
    print(f"\nFinal Pod Counts - Requester: {final_requester_count} (was {initial_requester_count}), Provider: {final_provider_count} (was {initial_provider_count})")
    print(f"Final HPA Status:")
    print(get_hpa_status())
    print("=" * 100)

if __name__ == "__main__":
    import sys
    
    # Get requester URL from command line or use default
    requester_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5003"
    
    # Generate load for 5 minutes with 5 requests per second
    generate_load(requester_url, duration=300, requests_per_second=5) 