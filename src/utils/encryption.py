"""
Utilitaires de chiffrement pour données sensibles.
Utilise Fernet (AES 128-bit CBC) pour le chiffrement symétrique.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from .logging import get_logger

logger = get_logger(__name__)


def get_encryption_key() -> bytes:
    """
    Génère ou récupère la clé de chiffrement depuis l'environnement.

    Returns:
        Clé Fernet (32 bytes base64-encoded)

    Raises:
        ValueError: Si la clé est invalide

    Note:
        La clé doit être définie dans AUTH_ENCRYPTION_KEY (environnement).
        Si absente, génère une clé temporaire (⚠️ ne pas utiliser en prod!).
    """
    # Lire depuis environnement
    key_b64 = os.getenv("AUTH_ENCRYPTION_KEY")

    if key_b64:
        try:
            # Valider la clé Fernet (doit être 44 caractères base64)
            key = base64.urlsafe_b64decode(key_b64)
            if len(key) != 32:
                raise ValueError(f"Invalid key length: {len(key)} (expected 32 bytes)")
            return key
        except Exception as e:
            logger.error(f"Invalid AUTH_ENCRYPTION_KEY format: {e}")
            raise ValueError(f"AUTH_ENCRYPTION_KEY is invalid: {e}")

    # Fallback : générer clé temporaire (⚠️ DEV ONLY!)
    logger.critical(
        "⚠️  AUTH_ENCRYPTION_KEY not set! Generating temporary key. "
        "THIS IS INSECURE FOR PRODUCTION! Set AUTH_ENCRYPTION_KEY in your .env file."
    )

    # Générer clé depuis un salt fixe (reproductible mais INSECURE)
    # En production, utiliser Fernet.generate_key() et stocker dans .env
    password = b"linkedin-bot-temp-key-CHANGE-ME"
    salt = b"static-salt-rpi4-INSECURE"

    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))

    logger.warning(f"Temporary encryption key generated (first 16 chars): {key[:16].decode()}...")
    return base64.urlsafe_b64decode(key)


def encrypt_json(data: dict) -> str:
    """
    Chiffre un dictionnaire JSON et retourne une string base64.

    Args:
        data: Dictionnaire à chiffrer

    Returns:
        String base64 du contenu chiffré

    Raises:
        Exception: Si le chiffrement échoue
    """
    import json

    key = get_encryption_key()
    fernet = Fernet(key)

    # Sérialiser JSON (compact pour réduire taille)
    json_bytes = json.dumps(data, separators=(',', ':')).encode('utf-8')

    # Chiffrer
    encrypted_bytes = fernet.encrypt(json_bytes)

    # Encoder en base64 pour stockage
    return base64.b64encode(encrypted_bytes).decode('utf-8')


def decrypt_json(encrypted_b64: str) -> dict:
    """
    Déchiffre une string base64 et retourne un dictionnaire JSON.

    Args:
        encrypted_b64: String base64 du contenu chiffré

    Returns:
        Dictionnaire déchiffré

    Raises:
        InvalidToken: Si le déchiffrement échoue (clé invalide ou données corrompues)
        Exception: Si le parsing JSON échoue
    """
    import json

    key = get_encryption_key()
    fernet = Fernet(key)

    # Décoder base64
    encrypted_bytes = base64.b64decode(encrypted_b64)

    # Déchiffrer (lève InvalidToken si la clé est mauvaise)
    decrypted_bytes = fernet.decrypt(encrypted_bytes)

    # Parser JSON
    return json.loads(decrypted_bytes.decode('utf-8'))


def generate_new_key() -> str:
    """
    Génère une nouvelle clé Fernet aléatoire sécurisée.

    Returns:
        Clé Fernet encodée en base64 (44 caractères)

    Usage:
        >>> from src.utils.encryption import generate_new_key
        >>> new_key = generate_new_key()
        >>> print(f"Add this to your .env: AUTH_ENCRYPTION_KEY={new_key}")
    """
    return Fernet.generate_key().decode('utf-8')


if __name__ == "__main__":
    # Test du module
    print("🔐 Encryption Module Test")
    print("=" * 50)

    # Générer une nouvelle clé
    new_key = generate_new_key()
    print(f"\n✅ New encryption key generated:")
    print(f"AUTH_ENCRYPTION_KEY={new_key}")
    print(f"\n⚠️  Add this to your .env file!")

    # Test chiffrement/déchiffrement
    print("\n" + "=" * 50)
    print("Testing encryption/decryption...")

    test_data = {
        "cookies": [
            {"name": "li_at", "value": "test_session_token_12345"},
            {"name": "JSESSIONID", "value": "ajax:1234567890"}
        ],
        "origins": ["https://www.linkedin.com"]
    }

    try:
        # Chiffrer
        encrypted = encrypt_json(test_data)
        print(f"✅ Encrypted (first 50 chars): {encrypted[:50]}...")

        # Déchiffrer
        decrypted = decrypt_json(encrypted)
        print(f"✅ Decrypted successfully")
        print(f"   Cookies count: {len(decrypted.get('cookies', []))}")

        # Vérifier intégrité
        assert decrypted == test_data, "Data mismatch!"
        print(f"✅ Data integrity verified")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 50)
    print("✅ All tests passed!")
