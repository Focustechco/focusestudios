import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.config import settings
from app.models.account import Account

# Forçar ambiente de testes
settings.OPERATION_MODE = "DEMO"
settings.DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Conta TikTok demo para testes
    acc = Account(
        open_id="test_open_id",
        username="@test_creator",
        display_name="Test Creator",
        privacy_options="PUBLIC_TO_EVERYONE,MUTUAL_FOLLOW_FRIENDS,SELF_ONLY",
        is_eligible=True,
        is_active=True
    )
    acc.access_token = "valid_test_token"
    acc.refresh_token = "valid_refresh_token"
    db.add(acc)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
