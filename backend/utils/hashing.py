import hashlib


def generate_hash(file_path: str) -> str:
    """SHA-256 hash of a file. Reads in 64KB chunks so large models don't blow memory."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_bytes(data: bytes) -> str:
    """SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def verify_hash(file_path: str, expected_hash: str) -> bool:
    """Quick check: does this file still match the stored hash?"""
    return generate_hash(file_path) == expected_hash
