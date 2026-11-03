import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.security import token_cipher
from app.core.timezone import get_current_time_utc


class Account(Base):
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform = Column(String(50), default="tiktok", nullable=False)  # tiktok
    open_id = Column(String(255), unique=True, index=True, nullable=False)
    union_id = Column(String(255), nullable=True)
    username = Column(String(100), nullable=False)
    display_name = Column(String(150), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Tokens criptografados em repouso
    _access_token_encrypted = Column("access_token", Text, nullable=True)
    _refresh_token_encrypted = Column("refresh_token", Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    refresh_expires_at = Column(DateTime, nullable=True)
    scopes = Column(String(255), default="user.info.basic,video.publish", nullable=False)

    # Capacidades e Elegibilidade consultadas via /v2/post/publish/creator_info/query/
    privacy_options = Column(Text, default="PUBLIC_TO_EVERYONE,MUTUAL_FOLLOW_FRIENDS,SELF_ONLY")
    comment_disabled = Column(Boolean, default=False)
    duet_disabled = Column(Boolean, default=False)
    stitch_disabled = Column(Boolean, default=False)
    max_video_duration_sec = Column(String(20), default="600")
    
    # Status de elegibilidade
    is_active = Column(Boolean, default=True)
    is_eligible = Column(Boolean, default=False)
    eligibility_notes = Column(Text, default="Requer aprovação oficial de Direct Post ou conta sandbox.")

    created_at = Column(DateTime, default=get_current_time_utc)
    updated_at = Column(DateTime, default=get_current_time_utc, onupdate=get_current_time_utc)

    # Relacionamentos
    post_drafts = relationship("PostDraft", back_populates="account")
    scheduled_posts = relationship("ScheduledPost", back_populates="account")

    @property
    def access_token(self) -> str:
        return token_cipher.decrypt(self._access_token_encrypted or "")

    @access_token.setter
    def access_token(self, value: str):
        self._access_token_encrypted = token_cipher.encrypt(value)

    @property
    def refresh_token(self) -> str:
        return token_cipher.decrypt(self._refresh_token_encrypted or "")

    @refresh_token.setter
    def refresh_token(self, value: str):
        self._refresh_token_encrypted = token_cipher.encrypt(value)

    def is_token_expired(self) -> bool:
        if not self.token_expires_at:
            return True
        from app.core.timezone import to_utc, get_current_time_utc
        return get_current_time_utc() >= to_utc(self.token_expires_at)
