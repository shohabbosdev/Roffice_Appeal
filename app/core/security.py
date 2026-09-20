import hashlib
import hmac
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random salt."""
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()
    return f"{salt}${key}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored salt$hash."""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()
        return key == stored_hash
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.STAFF_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def create_telegram_bind_token(user_id: int) -> str:
    """Generate 15-minute cryptographically signed token for Telegram account binding."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode = {"sub": str(user_id), "type": "tg_bind", "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_telegram_bind_token(token_str: str) -> Optional[int]:
    """Verify signed Telegram bind token and return user_id if valid."""
    try:
        payload = jwt.decode(token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "tg_bind":
            return None
        return int(payload.get("sub"))
    except Exception:
        return None


def encrypt_secret(plaintext: str) -> str:
    """
    Simmetrik shifrlash: Standart kutubxona (PBKDF2 + Keystream + HMAC-SHA256).
    Maxfiy tokenlarni bazada ochiq matn holda qoldirmaslik uchun xavfsiz shifrlaydi.
    Format: enc$v1${salt_hex}${mac_hex}${cipher_hex}
    """
    if not plaintext:
        return ""
    salt = os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", settings.SECRET_KEY.encode("utf-8"), salt, 10000)
    data = plaintext.encode("utf-8")
    
    # Keystream generator
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(data):
        block = hashlib.sha256(derived_key + counter.to_bytes(4, "big")).digest()
        keystream.extend(block)
        counter += 1
    
    ciphertext = bytes(a ^ b for a, b in zip(data, keystream[:len(data)]))
    mac = hmac.new(derived_key, ciphertext, hashlib.sha256).digest()
    return f"enc$v1${salt.hex()}${mac.hex()}${ciphertext.hex()}"


def decrypt_secret(ciphertext_bundle: str) -> str:
    """
    Shifrlangan tokenni ochish va tekshirish.
    Agar bundle shifrlanmagan bo'lsa (eski qiymat), uni to'g'ridan-to'g'ri qaytaradi.
    """
    if not ciphertext_bundle:
        return ""
    if not ciphertext_bundle.startswith("enc$v1$"):
        return ciphertext_bundle

    try:
        parts = ciphertext_bundle.split("$")
        if len(parts) != 5:
            return ""
        salt = bytes.fromhex(parts[2])
        mac = bytes.fromhex(parts[3])
        ciphertext = bytes.fromhex(parts[4])

        derived_key = hashlib.pbkdf2_hmac("sha256", settings.SECRET_KEY.encode("utf-8"), salt, 10000)
        expected_mac = hmac.new(derived_key, ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected_mac):
            return ""

        keystream = bytearray()
        counter = 0
        while len(keystream) < len(ciphertext):
            block = hashlib.sha256(derived_key + counter.to_bytes(4, "big")).digest()
            keystream.extend(block)
            counter += 1

        plaintext_bytes = bytes(a ^ b for a, b in zip(ciphertext, keystream[:len(ciphertext)]))
        return plaintext_bytes.decode("utf-8")
    except Exception:
        return ""


def mask_secret(secret: str, prefix_len: int = 6, suffix_len: int = 4) -> str:
    """Tokenni UI uchun xavfsiz maskalash (masalan: 857197...3Yk)."""
    if not secret:
        return ""
    if len(secret) <= (prefix_len + suffix_len):
        return "********"
    return f"{secret[:prefix_len]}...{secret[-suffix_len:]}"
