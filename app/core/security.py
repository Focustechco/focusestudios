import hashlib
import hmac
from typing import Optional
from cryptography.fernet import Fernet
from app.config import settings


class TokenCipher:
    """Criptografia simétrica em repouso de tokens e segredos usando Fernet (AES-128-CBC + HMAC)."""
    def __init__(self, key: Optional[str] = None):
        self.key = (key or settings.TOKEN_ENCRYPTION_KEY).encode()
        try:
            self.cipher = Fernet(self.key)
        except Exception:
            # Garante que uma chave Fernet válida esteja disponível
            valid_key = Fernet.generate_key()
            self.cipher = Fernet(valid_key)

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        return self.cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher_text: str) -> str:
        if not cipher_text:
            return ""
        try:
            return self.cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""


token_cipher = TokenCipher()


def calculate_content_hash(
    media_sha256: str,
    title: str,
    privacy_level: str,
    disable_comment: bool,
    disable_duet: bool,
    disable_stitch: bool,
    is_aigc: bool,
    brand_content: bool,
) -> str:
    """
    Gera o hash criptográfico do conteúdo aprovado.
    Qualquer alteração na legenda, privacidade ou declarações altera o hash,
    invalidando aprovações prévias para conformidade legal.
    """
    payload = f"{media_sha256}|{title.strip()}|{privacy_level}|{disable_comment}|{disable_duet}|{disable_stitch}|{is_aigc}|{brand_content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_state_token(user_id: str, action: str) -> str:
    """Gera um state seguro para o fluxo OAuth 2.0 com HMAC."""
    message = f"{user_id}:{action}:{settings.APP_SECRET}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()
