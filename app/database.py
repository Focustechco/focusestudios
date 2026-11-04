from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from contextlib import contextmanager
from app.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

_tables_initialized = False


def init_db():
    """Garante a criação de todas as tabelas, essencial para cold starts em serverless (Vercel)."""
    global _tables_initialized
    if not _tables_initialized:
        try:
            import app.models  # Garante registro de todos os modelos no Base.metadata
            Base.metadata.create_all(bind=engine)
            _tables_initialized = True
        except Exception as e:
            # Não quebra caso ocorra lock temporário ou erro de permissão
            print(f"[Database] Aviso ao criar tabelas: {e}")


def get_db():
    """Gerador de sessão de banco para injeção de dependência no FastAPI."""
    init_db()
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Gerenciador de contexto para Celery tasks, scripts de migração e testes."""
    init_db()
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
