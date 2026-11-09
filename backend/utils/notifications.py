import os
import base64
from cryptography.fernet import Fernet
from backend.auth.jwt_handler import SECRET_KEY

# Derive Fernet key from SECRET_KEY (first 32 chars, base64 encoded)
fernet_key = base64.urlsafe_b64encode(SECRET_KEY[:32].encode()).decode()
_cipher = Fernet(fernet_key.encode())


def encrypt_data(data: str) -> str:
    """Encrypt string data using Fernet."""
    return _cipher.encrypt(data.encode()).decode()


def decrypt_data(encrypted: str) -> str:
    """Decrypt Fernet-encrypted string."""
    return _cipher.decrypt(encrypted.encode()).decode()


def encrypt_json(data: dict) -> str:
    """Encrypt a JSON-serializable dict."""
    import json
    return encrypt_data(json.dumps(data))


def decrypt_json(encrypted: str) -> dict:
    """Decrypt to JSON dict."""
    import json
    return json.loads(decrypt_data(encrypted))


# Push notification functions (to be implemented in Phase 6)
async def send_push_notification(user_id: int, title: str, body: str, data: dict = None):
    """Send push notification to user (web push / email / in-app)."""
    # TODO: Implement with firebase/web-push/email
    pass


async def send_emergency_alert(user_id: int, message: str, contact_name: str):
    """Send high-priority emergency alert."""
    # TODO: Implement with multiple channels (push, email, SMS)
    pass