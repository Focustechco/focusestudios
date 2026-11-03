from datetime import timedelta
from app.models.account import Account
from app.core.timezone import get_current_time_utc


def test_token_expiration_detection(db_session):
    account = db_session.query(Account).filter_by(open_id="test_open_id").first()
    
    # Token válido no futuro
    account.token_expires_at = get_current_time_utc() + timedelta(hours=2)
    assert account.is_token_expired() is False

    # Token expirado no passado
    account.token_expires_at = get_current_time_utc() - timedelta(minutes=5)
    assert account.is_token_expired() is True


def test_token_encryption_at_rest(db_session):
    account = db_session.query(Account).filter_by(open_id="test_open_id").first()
    
    # Define um token novo
    secret_token_val = "secret_tiktok_bearer_token_xyz123"
    account.access_token = secret_token_val
    db_session.commit()

    # O getter deve retornar o token descriptografado
    assert account.access_token == secret_token_val

    # O campo bruto da coluna no banco (_access_token_encrypted) NÃO deve conter o texto plano
    raw_in_db = account._access_token_encrypted
    assert raw_in_db != secret_token_val
    assert "gAAAAA" in raw_in_db  # Prefixo padrão do Fernet
