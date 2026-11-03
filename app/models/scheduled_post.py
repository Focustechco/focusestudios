import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.timezone import get_current_time_utc


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_draft_id = Column(String(36), ForeignKey("post_drafts.id"), nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)

    # Persistência em UTC, exibição em America/Fortaleza
    scheduled_time_utc = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="SCHEDULED", index=True, nullable=False)

    # Concorrência e bloqueio atômico (SKIP LOCKED)
    lock_id = Column(String(64), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    priority = Column(Integer, default=0)

    created_at = Column(DateTime, default=get_current_time_utc)
    updated_at = Column(DateTime, default=get_current_time_utc, onupdate=get_current_time_utc)

    # Relacionamentos
    post_draft = relationship("PostDraft", back_populates="scheduled_posts")
    account = relationship("Account", back_populates="scheduled_posts")
    publish_attempts = relationship("PublishAttempt", back_populates="scheduled_post", cascade="all, delete-orphan")
