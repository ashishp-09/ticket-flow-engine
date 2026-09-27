import hashlib
import hmac
import secrets


class PasswordManager:
    def __init__(self, algorithm: str = "sha256", iterations: int = 600000):
        self.algorithm = algorithm
        self.iterations = iterations

    async def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        hashed_bytes = hashlib.pbkdf2_hmac(self.algorithm, password.encode("utf-8"), salt, self.iterations)
        return f"{salt.hex()}:{hashed_bytes.hex()}"

    async def verify_password(self, plain_password: str, stored_password_string: str) -> bool:
        try:
            salt_hex, original_hash_hex = stored_password_string.split(":")
            salt = bytes.fromhex(salt_hex)
        except (ValueError, AttributeError):
            return False

        new_hash_bytes = hashlib.pbkdf2_hmac(self.algorithm, plain_password.encode("utf-8"), salt, self.iterations)
        return hmac.compare_digest(new_hash_bytes.hex(), original_hash_hex)
