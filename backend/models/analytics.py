from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.sql import func
from backend.database import Base
import enum


class AnalyticsEventType(str, enum.Enum):
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    AUTO_REPLY_SENT = "auto_reply_sent"
    REPLY_SUGGESTED = "reply_suggested"
    EMERGENCY_TRIGGERED = "emergency_triggered"
    BUSY_MODE_TOGGLED = "busy_mode_toggled"
    PLATFORM_CONNECTED = "platform_connected"
    PLATFORM_DISCONNECTED = "platform_disconnected"


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(SQLEnum(AnalyticsEventType), nullable=False, index=True)
    platform = Column(String(20), nullable=True, index=True)

    # Optional context
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)

    # Metadata (JSON string)
    event_metadata = Column("metadata", Text, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("ix_analytics_user_type_time", "user_id", "event_type", "timestamp"),
        Index("ix_analytics_user_platform_time", "user_id", "platform", "timestamp"),
    )
