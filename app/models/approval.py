import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.timezone import get_current_time_utc


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_draft_id = Column(String(36), ForeignKey("post_drafts.id"), nullable=False)
    
    approved_by = Column(String(100), default="operador")
    approved_at = Column(DateTime, default=get_current_time_utc, nullable=False)
    
    # Hash do conteúdo aprovado (SHA-256)
    content_hash = Column(String(64), nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(String(255), nullable=True)

    post_draft = relationship("PostDraft", back_populates="approvals")
