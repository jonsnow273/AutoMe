import base64
import hashlib
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_change_in_production")


def _get_fernet_key() -> bytes:
    # Derive a 32-byte url-safe base64-encoded key from SECRET_KEY
    key_hash = hashlib.sha256(SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key_hash)


def encrypt_string(plain_text: str) -> str:
    """Encrypt a string and return ciphertext as a UTF-8 string."""
    if not plain_text:
        return ""
    f = Fernet(_get_fernet_key())
    return f.encrypt(plain_text.encode()).decode()


def decrypt_string(cipher_text: str) -> str:
    """Decrypt a ciphertext string back to plain text."""
    if not cipher_text:
        return ""
    try:
        f = Fernet(_get_fernet_key())
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        return ""
