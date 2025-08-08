#!/usr/bin/env python3
"""
Demo script for JWT-based node registration with node.py
This shows how to:
1. Get a JWT token from the issuer
2. Use the token to register nodes with the blockchain
"""

import requests
import json

# Configuration
ISSUER_URL = "http://localhost:8443"  # Local port-forward URL
MASTER_URL = "http://localhost:5002"  # Local port-forward URL

# Real API key (should match one in VALID_KEYS environment variable)
API_KEY = "GxhLsgzHORw1rTDJMX3L2T85i9r52bQlLIhWxpGYjhA="

def demo_jwt_registration():
    """Demonstrate JWT-based node registration."""
    print("JWT-based Node Registration Demo")
    print("="*40)
    
    # Step 1: Get JWT token
    print("1. Getting JWT token from issuer...")
    try:
        response = requests.post(
            f"{ISSUER_URL}/token",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            jwt_token = token_data["token"]
            print(f"   ✓ Token obtained (expires in {token_data['expires_in']}s)")
        else:
            print(f"   ✗ Failed to get token: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Step 2: Register nodes with JWT
    print("\n2. Registering nodes with JWT authentication...")
    registration_data = {
        "nodes": ["http://node1:5001", "http://node2:5002"],
        "role": "provider",
        "is_local": False
    }
    
    try:
        response = requests.post(
            f"{MASTER_URL}/nodes/register",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            },
            json=registration_data,
            timeout=10
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"   ✓ Registration successful")
            print(f"   ✓ Message: {result['message']}")
            print(f"   ✓ Peers: {len(result['peers'])} total")
            for peer in result['peers']:
                print(f"      - {peer['address']} ({peer['role']})")
        else:
            print(f"   ✗ Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n" + "="*40)
    print("✓ JWT authentication demo completed successfully!")
    return True

def demo_without_jwt():
    """Demonstrate registration without JWT (should fail)."""
    print("\nDemo: Registration without JWT (should fail)")
    print("="*40)
    
    registration_data = {
        "nodes": ["http://node3:5003"],
        "role": "requester",
        "is_local": False
    }
    
    try:
        response = requests.post(
            f"{MASTER_URL}/nodes/register",
            headers={"Content-Type": "application/json"},
            json=registration_data,
            timeout=10
        )
        
        if response.status_code == 401:
            print(f"   ✓ Correctly rejected (401 Unauthorized)")
            print(f"   ✓ Error: {response.json().get('error', 'Unknown error')}")
        else:
            print(f"   ⚠ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

if __name__ == '__main__':
    # Run JWT demo
    success = demo_jwt_registration()
    
    if success:
        # Show fallback behavior
        demo_without_jwt()
        
        print("\n" + "="*40)
        print("Demo completed!")
        print("\nKey features:")
        print("- JWT authentication is MANDATORY for all protected operations")
        print("- Valid JWT tokens are verified with scope checking")
        print("- Missing or invalid tokens are rejected with 401 errors")
        print("- Public endpoints remain accessible without JWT")
        print("\nJWT Scopes implemented:")
        print("- blockchain:register - Node registration")
        print("- blockchain:mine - Mining operations")
        print("- blockchain:receive_block - Block acceptance")
        print("- blockchain:sync - Chain synchronization")
        print("- blockchain:metrics - Metrics access")
    else:
        print("\nDemo failed. Check service availability.") 