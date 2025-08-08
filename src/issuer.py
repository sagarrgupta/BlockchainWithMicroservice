#!/usr/bin/env python3
"""
JWT Issuer Service
Issues JWT tokens for node registration using RSA signing.
"""

import os
import jwt
import base64
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
ISSUER_PORT = int(os.environ.get("ISSUER_PORT", "8443"))
NODE_ID = os.environ.get("NODE_ID", "default-node")
VALID_KEYS = os.environ.get("VALID_KEYS", "").split(",") if os.environ.get("VALID_KEYS") else []

# Load private key for signing
PRIVATE_KEY_PATH = "/secrets/private.pem"

def load_private_key():
    """Load the RSA private key for signing JWTs."""
    try:
        with open(PRIVATE_KEY_PATH, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: Private key not found at {PRIVATE_KEY_PATH}")
        return None
    except Exception as e:
        print(f"ERROR: Failed to load private key: {e}")
        return None

def generate_node_api_key():
    """Generate a random 32-byte base64 API key for node identification."""
    return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "jwt-issuer"})

@app.route('/token', methods=['POST'])
def issue_token():
    """
    Issue a JWT token for node registration.
    
    Expected headers:
    - Authorization: Bearer <API_KEY>
    
    Returns:
    - 200: JWT token
    - 401: Invalid API key
    - 500: Server error
    """
    try:
        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        
        api_key = auth_header.split(' ')[1]
        
        # Validate API key
        if api_key not in VALID_KEYS:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Load private key
        private_key = load_private_key()
        if not private_key:
            return jsonify({"error": "Failed to load signing key"}), 500
        
        # Create JWT payload
        now = datetime.utcnow()
        payload = {
            'sub': NODE_ID,
            'iat': now,
            'exp': now + timedelta(minutes=10),  # 10 minute expiration
            'iss': 'blockchain-node-issuer',
            'aud': 'blockchain-master',
            'scope': 'blockchain:register blockchain:mine blockchain:receive_block blockchain:sync blockchain:metrics'
        }
        
        # Sign JWT with RS256
        token = jwt.encode(payload, private_key, algorithm='RS256')
        
        return jsonify({
            "token": token,
            "expires_in": 600,  # 10 minutes in seconds
            "token_type": "Bearer"
        }), 200
        
    except jwt.PyJWTError as e:
        return jsonify({"error": f"JWT encoding error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/generate-api-key', methods=['POST'])
def generate_api_key():
    """
    Generate a new API key for node registration.
    This endpoint is for administrative purposes.
    """
    new_api_key = generate_node_api_key()
    return jsonify({
        "api_key": new_api_key,
        "message": "Add this key to VALID_KEYS environment variable"
    }), 200

if __name__ == '__main__':
    # Validate configuration
    if not VALID_KEYS:
        print("WARNING: No valid API keys configured. Set VALID_KEYS environment variable.")
    
    if not os.path.exists(PRIVATE_KEY_PATH):
        print(f"WARNING: Private key not found at {PRIVATE_KEY_PATH}")
        print("Make sure the JWT issuer key secret is properly mounted.")
    
    print(f"Starting JWT Issuer on port {ISSUER_PORT}")
    print(f"Node ID: {NODE_ID}")
    print(f"Valid API keys: {len(VALID_KEYS)} configured")
    
    app.run(host='0.0.0.0', port=ISSUER_PORT, debug=False) 