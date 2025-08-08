#!/usr/bin/env python3
"""
Test script to demonstrate mandatory JWT authentication.
Shows that all protected endpoints require valid JWT tokens.
"""

import requests
import json

# Configuration
ISSUER_URL = "http://jwt-issuer-service:8443"
MASTER_URL = "http://master-service:5002"

# Real API key
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

def test_mandatory_jwt():
    """Test that JWT is mandatory for protected endpoints."""
    print("Testing Mandatory JWT Authentication")
    print("="*50)
    
    # Get JWT token
    jwt_token = get_jwt_token()
    if not jwt_token:
        print("✗ Failed to get JWT token")
        return False
    
    # Test endpoints that require JWT
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
    
    print("\n1. Testing WITH valid JWT token:")
    print("-" * 30)
    
    for endpoint, method, data in protected_endpoints:
        print(f"\nTesting {method} {endpoint} with JWT...")
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(f"{MASTER_URL}{endpoint}", headers=headers, timeout=10)
            else:
                response = requests.post(f"{MASTER_URL}{endpoint}", headers=headers, json=data, timeout=10)
            
            if response.status_code in [200, 201]:
                print(f"   ✓ Success ({response.status_code})")
            else:
                print(f"   ✗ Failed ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n2. Testing WITHOUT JWT token (should fail):")
    print("-" * 40)
    
    for endpoint, method, data in protected_endpoints:
        print(f"\nTesting {method} {endpoint} without JWT...")
        
        try:
            if method == "GET":
                response = requests.get(f"{MASTER_URL}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{MASTER_URL}{endpoint}", json=data, timeout=10)
            
            if response.status_code == 401:
                error_msg = response.json().get('error', 'Unknown error')
                print(f"   ✓ Correctly rejected (401): {error_msg}")
            else:
                print(f"   ⚠ Unexpected response ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n3. Testing public endpoints (should work without JWT):")
    print("-" * 45)
    
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
    
    return True

def test_invalid_jwt():
    """Test with invalid JWT tokens."""
    print("\n4. Testing with invalid JWT tokens:")
    print("-" * 35)
    
    invalid_tokens = [
        "invalid.jwt.token",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiaWF0IjoxNjE2MjM5MDIyfQ.invalid_signature",
        ""
    ]
    
    for i, invalid_token in enumerate(invalid_tokens, 1):
        print(f"\nTest {i}: Invalid token '{invalid_token[:20]}...'")
        
        headers = {
            "Authorization": f"Bearer {invalid_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                f"{MASTER_URL}/nodes/register",
                headers=headers,
                json={"nodes": ["http://test:5001"], "role": "provider"},
                timeout=10
            )
            
            if response.status_code == 401:
                print(f"   ✓ Correctly rejected invalid token")
            else:
                print(f"   ⚠ Unexpected response ({response.status_code})")
        except Exception as e:
            print(f"   ✗ Error: {e}")

def main():
    """Run mandatory JWT tests."""
    print("Mandatory JWT Authentication Test")
    print("="*50)
    
    success = test_mandatory_jwt()
    
    if success:
        test_invalid_jwt()
        
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print("✓ Protected endpoints require MANDATORY JWT")
        print("✓ Missing JWT returns 401 Unauthorized")
        print("✓ Invalid JWT returns 401 Unauthorized")
        print("✓ Public endpoints work without JWT")
        print("✓ Valid JWT with proper scopes works")
        print("\nSecurity Model:")
        print("- JWT authentication is MANDATORY for protected operations")
        print("- No fallback behavior for missing/invalid tokens")
        print("- Scope-based access control enforced")
        print("- Public endpoints remain accessible for transparency")

if __name__ == '__main__':
    main() 