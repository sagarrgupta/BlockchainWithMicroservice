#!/usr/bin/env python3
"""
Test script to demonstrate JWT-based node registration flow.
This script shows how to:
1. Get a JWT token from the issuer
2. Use the token to register with the master
"""

import requests
import json
import base64
import secrets

# Configuration
ISSUER_URL = "http://jwt-issuer-service:8443"  # In-cluster URL
MASTER_URL = "http://master-service:5002"       # In-cluster URL (uses /nodes/register endpoint)

# Real API key (should match one in VALID_KEYS environment variable)
API_KEY = "GxhLsgzHORw1rTDJMX3L2T85i9r52bQlLIhWxpGYjhA="

def test_jwt_flow():
    """Test the complete JWT authentication flow."""
    print("Testing JWT-based node registration flow...")
    print("="*50)
    
    # Step 1: Get JWT token from issuer
    print("Step 1: Getting JWT token from issuer...")
    try:
        response = requests.post(
            f"{ISSUER_URL}/token",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            jwt_token = token_data["token"]
            print(f"✓ JWT token obtained successfully")
            print(f"  Expires in: {token_data['expires_in']} seconds")
        else:
            print(f"✗ Failed to get JWT token: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error connecting to issuer: {e}")
        return False
    
    # Step 2: Register with master using JWT token
    print("\nStep 2: Registering with master using JWT token...")
    try:
        registration_data = {
            "nodes": ["test-node-1:5001", "test-node-2:5002"]
        }
        
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
            print(f"✓ Node registration successful")
            print(f"  Message: {result['message']}")
            print(f"  Peers: {len(result['peers'])} registered")
        else:
            print(f"✗ Failed to register with master: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error connecting to master: {e}")
        return False
    
    print("\n" + "="*50)
    print("✓ JWT authentication flow completed successfully!")
    return True

def test_invalid_api_key():
    """Test with invalid API key."""
    print("\nTesting with invalid API key...")
    invalid_key = "invalid-api-key"
    
    try:
        response = requests.post(
            f"{ISSUER_URL}/token",
            headers={
                "Authorization": f"Bearer {invalid_key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 401:
            print("✓ Correctly rejected invalid API key")
        else:
            print(f"✗ Unexpected response for invalid API key: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error testing invalid API key: {e}")

def test_expired_token():
    """Test with expired token (simulated)."""
    print("\nTesting with expired token...")
    
    # Create a token that's already expired
    import jwt
    from datetime import datetime, timedelta
    
    # This would need the actual private key to create a real expired token
    # For demonstration, we'll just show the concept
    print("Note: Testing expired tokens requires the actual private key")
    print("In a real scenario, you would create a token with exp in the past")

def main():
    """Run all JWT flow tests."""
    print("JWT Authentication Flow Test")
    print("="*50)
    
    # Test valid flow
    success = test_jwt_flow()
    
    if success:
        # Test error cases
        test_invalid_api_key()
        test_expired_token()
        
        print("\n" + "="*50)
        print("All tests completed!")
        print("\nTo run this test:")
        print("1. Deploy the JWT issuer and updated master")
        print("2. Run this script from within the cluster")
        print("3. Or use kubectl exec to run it in a pod")
    else:
        print("\n✗ JWT flow test failed. Check service availability.")

if __name__ == '__main__':
    main() 