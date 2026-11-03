import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.timezone import get_current_time_utc


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    drive_source_id = Column(String(36), ForeignKey("drive_sources.id"), nullable=True)
    drive_file_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    mime_type = Column(String(100), default="video/mp4")
    file_size_bytes = Column(Integer, nullable=False, default=0)
    
    # Hash SHA-256 para detecção de duplicatas cross-file
    sha256_hash = Column(String(64), index=True, nullable=False)
    md5_checksum = Column(String(64), nullable=True)

    # Inspeção técnica (FFmpeg/ffprobe)
    duration_seconds = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    aspect_ratio = Column(String(20), nullable=True)  # ex: 9:16, 16:9
    video_codec = Column(String(50), nullable=True)   # ex: h264, hevc
    audio_codec = Column(String(50), nullable=True)   # ex: aac
    has_audio = Column(String(10), default="yes")

    # Status de inspeção e integridade
    status = Column(String(50), default="DISCOVERED", index=True, nullable=False)
    validation_notes = Column(Text, nullable=True)

    local_storage_path = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    drive_modified_time = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=get_current_time_utc)
    updated_at = Column(DateTime, default=get_current_time_utc, onupdate=get_current_time_utc)

    # Relacionamentos
    drive_source = relationship("DriveSource", back_populates="media_assets")
    post_drafts = relationship("PostDraft", back_populates="media_asset", cascade="all, delete-orphan")
