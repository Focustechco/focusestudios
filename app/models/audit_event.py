import uuid
from sqlalchemy import Column, String, DateTime, Text
from app.database import Base
from app.core.timezone import get_current_time_utc


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=True)
    user_or_system = Column(String(100), default="system")
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_current_time_utc, nullable=False, index=True)
