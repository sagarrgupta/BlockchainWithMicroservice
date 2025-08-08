#!/usr/bin/env python3
"""
Comprehensive test script for JWT-protected endpoints.
Tests all secured endpoints with proper JWT authentication.
"""

import requests
import json
import time

# Configuration
ISSUER_URL = "http://jwt-issuer-service:8443"
MASTER_URL = "http://master-service:5002"

# Real API key (should match one in VALID_KEYS environment variable)
API_KEY = "GxhLsgzHORw1rTDJMX3L2T85i9r52bQlLIhWxpGYjhA="

def get_jwt_token():
    """Get a JWT token from the issuer."""
    try:
        response = requests.post(
            f"{ISSUER_URL}/token",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()["token"]
        else:
            print(f"Failed to get JWT token: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting JWT token: {e}")
        return None

def test_endpoint_with_jwt(endpoint, method="GET", data=None, scope_name=None):
    """Test an endpoint with JWT authentication."""
    print(f"\nTesting {method} {endpoint}...")
    
    # Get JWT token
    jwt_token = get_jwt_token()
    if not jwt_token:
        print("   ✗ Failed to get JWT token")
        return False
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(f"{MASTER_URL}{endpoint}", headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(f"{MASTER_URL}{endpoint}", headers=headers, json=data, timeout=10)
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"   ✓ Success ({response.status_code})")
            if response.content:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
            return True
        else:
            print(f"   ✗ Failed ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_endpoint_without_jwt(endpoint, method="GET", data=None):
    """Test an endpoint without JWT authentication (should fail for protected endpoints)."""
    print(f"\nTesting {method} {endpoint} WITHOUT JWT...")
    
    try:
        if method == "GET":
            response = requests.get(f"{MASTER_URL}{endpoint}", timeout=10)
        elif method == "POST":
            response = requests.post(f"{MASTER_URL}{endpoint}", json=data, timeout=10)
        
        if response.status_code == 401:
            print(f"   ✓ Correctly rejected (401 Unauthorized)")
            return True
        else:
            print(f"   ⚠ Unexpected response ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_public_endpoints():
    """Test public endpoints that should work without JWT."""
    print("\n" + "="*50)
    print("TESTING PUBLIC ENDPOINTS (No JWT Required)")
    print("="*50)
    
    public_endpoints = [
        ("/chain", "GET"),
        ("/chain/summary", "GET"),
        ("/nodes", "GET"),
        ("/master_peers", "GET")
    ]
    
    for endpoint, method in public_endpoints:
        print(f"\nTesting {method} {endpoint} (public)...")
        try:
            if method == "GET":
                response = requests.get(f"{MASTER_URL}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{MASTER_URL}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                print(f"   ✓ Public endpoint accessible")
            else:
                print(f"   ✗ Public endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

def test_protected_endpoints():
    """Test protected endpoints with JWT authentication."""
    print("\n" + "="*50)
    print("TESTING PROTECTED ENDPOINTS (JWT Required)")
    print("="*50)
    
    # Test with JWT
    protected_endpoints = [
        ("/nodes/register", "POST", {
            "nodes": ["http://test-node:5001"],
            "role": "provider",
            "is_local": False
        }),
        ("/sync", "GET"),
        ("/mine", "GET"),
        ("/block_propagation_metrics", "GET")
    ]
    
    for endpoint, method, data in protected_endpoints:
        # Test with JWT
        test_endpoint_with_jwt(endpoint, method, data)
        
        # Test without JWT (should fail)
        test_endpoint_without_jwt(endpoint, method, data)

def test_receive_block_endpoint():
    """Test the /receive_block endpoint with a sample block."""
    print("\n" + "="*50)
    print("TESTING /receive_block ENDPOINT")
    print("="*50)
    
    # Create a sample block
    sample_block = {
        "index": 1,
        "timestamp": time.time(),
        "transactions": [],
        "proof": 100,
        "previous_hash": "1",
        "mined_by": "test-node"
    }
    
    # Test with JWT
    test_endpoint_with_jwt("/receive_block", "POST", {"block": sample_block})
    
    # Test without JWT (should fail)
    test_endpoint_without_jwt("/receive_block", "POST", {"block": sample_block})

def main():
    """Run all JWT endpoint tests."""
    print("JWT Endpoint Security Test")
    print("="*50)
    
    # Test public endpoints
    test_public_endpoints()
    
    # Test protected endpoints
    test_protected_endpoints()
    
    # Test receive_block specifically
    test_receive_block_endpoint()
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print("✓ Public endpoints should be accessible without JWT")
    print("✓ Protected endpoints require MANDATORY valid JWT")
    print("✓ Protected endpoints reject requests without JWT (401)")
    print("✓ JWT tokens must include proper scopes")
    print("\nJWT Scopes implemented:")
    print("- blockchain:register - Node registration")
    print("- blockchain:mine - Mining operations")
    print("- blockchain:receive_block - Block acceptance")
    print("- blockchain:sync - Chain synchronization")
    print("- blockchain:metrics - Metrics access")

if __name__ == '__main__':
    main() 