import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.core.timezone import get_current_time_utc


class PublishAttempt(Base):
    __tablename__ = "publish_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheduled_post_id = Column(String(36), ForeignKey("scheduled_posts.id"), nullable=False)

    attempt_number = Column(Integer, default=1, nullable=False)
    publish_id = Column(String(255), nullable=True, index=True)
    status = Column(String(50), default="UPLOADING", nullable=False)
    
    started_at = Column(DateTime, default=get_current_time_utc, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)

    scheduled_post = relationship("ScheduledPost", back_populates="publish_attempts")
