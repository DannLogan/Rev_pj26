import bcrypt
from werkzeug.security import check_password_hash as check_legacy_hash


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if not 1 <= len(encoded) <= 72:
        raise ValueError("A senha deve ter até 72 bytes em UTF-8.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(stored: str, password: str) -> bool:
    if not stored.startswith(("$2a$", "$2b$", "$2y$")):
        return check_legacy_hash(stored, password)
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        return False
    try:
        return bcrypt.checkpw(encoded, stored.encode("ascii"))
    except ValueError:
        return False
