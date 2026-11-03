import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.timezone import get_current_time_utc


class DriveSource(Base):
    __tablename__ = "drive_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    folder_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), default="Pasta Principal")
    include_subfolders = Column(Boolean, default=False)
    sync_interval_minutes = Column(Integer, default=15)
    last_synced_at = Column(DateTime, nullable=True)
    sync_page_token = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=get_current_time_utc)
    updated_at = Column(DateTime, default=get_current_time_utc, onupdate=get_current_time_utc)

    media_assets = relationship("MediaAsset", back_populates="drive_source")
