"""
Password hashing with stdlib hashlib (PBKDF2-HMAC-SHA256). Avoids needing
bcrypt/argon2 compiled dependencies just to get this running on a new
server - swap in passlib/bcrypt later if you want, the interface below
is all that's called elsewhere in the app.
"""
import hashlib
import os
import hmac

ITERATIONS = 260_000


def hash_password(password: str) -> tuple[str, str]:
    """Returns (password_hash_hex, salt_hex)."""
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return pw_hash.hex(), salt.hex()


def verify_password(password: str, password_hash_hex: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return hmac.compare_digest(candidate.hex(), password_hash_hex)
