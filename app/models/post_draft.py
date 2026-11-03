import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.timezone import get_current_time_utc


class PostDraft(Base):
    __tablename__ = "post_drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    media_asset_id = Column(String(36), ForeignKey("media_assets.id"), nullable=False)
    account_id = Column(String(36), ForeignKey("accounts.id"), nullable=True)

    title = Column(String(255), nullable=False)
    caption = Column(Text, nullable=False, default="")
    hashtags = Column(String(255), default="#focustech #produtividade")

    # Opções de publicação TikTok
    privacy_level = Column(String(50), default="SELF_ONLY")  # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, FOLLOWER_OF_CREATOR, SELF_ONLY
    disable_comment = Column(Boolean, default=False)
    disable_duet = Column(Boolean, default=False)
    disable_stitch = Column(Boolean, default=False)

    # Declarações obrigatórias
    is_aigc = Column(Boolean, default=False)  # Conteúdo gerado por IA
    brand_content_toggle = Column(Boolean, default=False)  # Conteúdo de marca
    brand_organic_toggle = Column(Boolean, default=False)  # Promocional próprio

    status = Column(String(50), default="DRAFT", index=True, nullable=False)
    validation_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_current_time_utc)
    updated_at = Column(DateTime, default=get_current_time_utc, onupdate=get_current_time_utc)

    # Relacionamentos
    media_asset = relationship("MediaAsset", back_populates="post_drafts")
    account = relationship("Account", back_populates="post_drafts")
    approvals = relationship("Approval", back_populates="post_draft", cascade="all, delete-orphan")
    scheduled_posts = relationship("ScheduledPost", back_populates="post_draft", cascade="all, delete-orphan")
