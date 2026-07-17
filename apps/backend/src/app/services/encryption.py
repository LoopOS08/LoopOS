import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using AES-256-GCM"""
    
    def __init__(self):
        self.kms_client = boto3.client(
            'kms',
            region_name=settings.AWS_REGION
        )
    
    def generate_data_key(self) -> tuple[str, bytes]:
        """Generate a new data key from KMS"""
        try:
            response = self.kms_client.generate_data_key(
                KeyId=settings.AWS_KMS_KEY_ID,
                KeySpec='AES_256'
            )
            plaintext_key = response['Plaintext']
            encrypted_key = response['CiphertextBlob']
            
            # Return base64 encoded encrypted key and plaintext bytes
            return base64.b64encode(encrypted_key).decode('utf-8'), plaintext_key
        except ClientError as e:
            raise Exception(f"Failed to generate data key: {e}")
    
    def decrypt_data_key(self, encrypted_key_b64: str) -> bytes:
        """Decrypt a data key using KMS"""
        try:
            encrypted_key = base64.b64decode(encrypted_key_b64)
            response = self.kms_client.decrypt(
                CiphertextBlob=encrypted_key,
                KeyId=settings.AWS_KMS_KEY_ID
            )
            return response['Plaintext']
        except ClientError as e:
            raise Exception(f"Failed to decrypt data key: {e}")
    
    def encrypt(self, plaintext: str, encrypted_key_b64: str) -> str:
        """Encrypt plaintext using AES-256-GCM"""
        try:
            # Decrypt the data key
            key = self.decrypt_data_key(encrypted_key_b64)
            
            # Create AESGCM cipher
            aesgcm = AESGCM(key)
            
            # Generate random nonce (96 bits for GCM)
            nonce = AESGCM.generate_nonce(bit_length=96)
            
            # Encrypt the plaintext
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
            
            # Combine nonce and ciphertext, then base64 encode
            combined = nonce + ciphertext
            return base64.b64encode(combined).decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to encrypt data: {e}")
    
    def decrypt(self, ciphertext_b64: str, encrypted_key_b64: str) -> str:
        """Decrypt ciphertext using AES-256-GCM"""
        try:
            # Decrypt the data key
            key = self.decrypt_data_key(encrypted_key_b64)
            
            # Create AESGCM cipher
            aesgcm = AESGCM(key)
            
            # Decode base64 and separate nonce and ciphertext
            combined = base64.b64decode(ciphertext_b64)
            nonce = combined[:12]  # First 96 bits (12 bytes)
            ciphertext = combined[12:]
            
            # Decrypt the ciphertext
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise Exception(f"Failed to decrypt data: {e}")
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt OAuth credentials for storage"""
        try:
            # Generate new data key for this credential
            encrypted_key_b64, _ = self.generate_data_key()
            
            # Convert credentials to JSON string
            credentials_json = json.dumps(credentials)
            
            # Encrypt the credentials
            encrypted_credentials = self.encrypt(credentials_json, encrypted_key_b64)
            
            # Return combined format: encrypted_key:encrypted_credentials
            return f"{encrypted_key_b64}:{encrypted_credentials}"
        except Exception as e:
            raise Exception(f"Failed to encrypt credentials: {e}")
    
    def decrypt_credentials(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt OAuth credentials from storage"""
        try:
            # Split encrypted key and credentials
            parts = encrypted_data.split(':', 1)
            if len(parts) != 2:
                raise ValueError("Invalid encrypted data format")
            
            encrypted_key_b64, encrypted_credentials = parts
            
            # Decrypt the credentials
            credentials_json = self.decrypt(encrypted_credentials, encrypted_key_b64)
            
            # Parse JSON
            return json.loads(credentials_json)
        except Exception as e:
            raise Exception(f"Failed to decrypt credentials: {e}")


# Global encryption service instance
encryption_service = EncryptionService()