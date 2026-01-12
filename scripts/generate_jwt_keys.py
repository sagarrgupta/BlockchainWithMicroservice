#!/usr/bin/env python3
"""
Generate RSA keypair for JWT signing and verification.
This script creates the private and public keys needed for JWT authentication.
"""

import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import base64

def generate_rsa_keypair():
    """Generate RSA keypair for JWT signing."""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    return private_key, public_key

def save_key_to_pem(key, filename, is_private=True):
    """Save key to PEM format file."""
    if is_private:
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    else:
        pem = key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    with open(filename, 'wb') as f:
        f.write(pem)
    
    print(f"Saved {filename}")
    return pem

def get_base64_encoded_key(pem_bytes):
    """Convert PEM bytes to base64 for Kubernetes secret."""
    return base64.b64encode(pem_bytes).decode('utf-8')

def main():
    print("Generating RSA keypair for JWT authentication...")
    
    # Generate keypair
    private_key, public_key = generate_rsa_keypair()
    
    # Save keys to files
    private_pem = save_key_to_pem(private_key, 'private.pem', is_private=True)
    public_pem = save_key_to_pem(public_key, 'public.pem', is_private=False)
    
    # Generate base64 encoded versions for Kubernetes secrets
    private_b64 = get_base64_encoded_key(private_pem)
    public_b64 = get_base64_encoded_key(public_pem)
    
    print("\n" + "="*50)
    print("KUBERNETES SECRET VALUES")
    print("="*50)
    print("Replace the placeholder values in k8s-jwt-secrets.yaml with:")
    print(f"\nprivate.pem: {private_b64}")
    print(f"\npublic.pem: {public_b64}")
    print("\n" + "="*50)
    
    # Generate example API keys
    import secrets
    api_key_1 = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
    api_key_2 = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
    
    print("\nEXAMPLE API KEYS (for VALID_KEYS environment variable):")
    print(f"api-key-1: {api_key_1}")
    print(f"api-key-2: {api_key_2}")
    print("\n" + "="*50)
    
    print("\nFiles created:")
    print("- private.pem (for JWT issuer)")
    print("- public.pem (for JWT verification)")
    
    print("\nNext steps:")
    print("1. Update k8s-jwt-secrets.yaml with the base64 encoded keys above")
    print("2. Apply the secrets: kubectl apply -f k8s-jwt-secrets.yaml")
    print("3. Deploy the services: kubectl apply -f k8s-jwt-issuer-deployment.yaml")
    print("4. Update master deployment: kubectl apply -f k8s-master-deployment.yaml")

if __name__ == '__main__':
    main() 