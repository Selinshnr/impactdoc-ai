import hashlib
from pathlib import Path


def calculate_sha256(path: Path) -> str:
    """
    Dosyanın SHA256 özetini hesaplar.
    """

    sha = hashlib.sha256()

    with open(path, "rb") as file:
        while chunk := file.read(8192):
            sha.update(chunk)

    return sha.hexdigest()