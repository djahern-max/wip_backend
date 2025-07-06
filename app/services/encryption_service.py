# app/services/encryption_service.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive contract data
    Uses Fernet (AES 128) encryption for database storage
    """

    def __init__(self):
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)

    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or generate new one"""

        # Check if key exists in environment
        if hasattr(settings, "encryption_key") and settings.encryption_key:
            return base64.urlsafe_b64decode(settings.encryption_key.encode())

        # Generate key from secret + salt for consistency
        password = settings.secret_key.encode()
        salt = b"contract_encryption_salt"  # In production, use random salt stored securely

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def encrypt_text(self, plaintext: str) -> str:
        """Encrypt text for database storage"""
        if not plaintext:
            return plaintext

        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode("utf-8"))
            return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")

    def decrypt_text(self, encrypted_text: str) -> str:
        """Decrypt text from database"""
        if not encrypted_text:
            return encrypted_text

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode("utf-8"))
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")

    def encrypt_file_content(self, file_content: bytes) -> str:
        """Encrypt file content for storage"""
        try:
            encrypted_bytes = self.cipher.encrypt(file_content)
            return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            raise Exception(f"File encryption failed: {str(e)}")

    def decrypt_file_content(self, encrypted_content: str) -> bytes:
        """Decrypt file content"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(
                encrypted_content.encode("utf-8")
            )
            return self.cipher.decrypt(encrypted_bytes)
        except Exception as e:
            raise Exception(f"File decryption failed: {str(e)}")


# Singleton instance
encryption_service = EncryptionService()
