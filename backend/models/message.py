from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


class MessageDirection(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class MessageMood(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"


class MessageUrgency(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class RelationshipType(str, enum.Enum):
    FRIEND = "friend"
    ACQUAINTANCE = "acquaintance"
    STRANGER = "stranger"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(String(20), nullable=False, index=True)  # discord, whatsapp, instagram
    platform_message_id = Column(String(100), nullable=False, index=True)

    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)

    content = Column(Text, nullable=False)
    direction = Column(SQLEnum(MessageDirection), nullable=False, default=MessageDirection.INCOMING)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)

    mood = Column(SQLEnum(MessageMood), nullable=True)
    urgency = Column(SQLEnum(MessageUrgency), nullable=True)
    relationship_type = Column(SQLEnum(RelationshipType), nullable=True)

    # AI-generated reply suggestion (for manual review)
    suggested_reply = Column(Text, nullable=True)
    reply_confidence = Column(Integer, nullable=True)  # 0-100

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Composite indexes for common queries
Index("ix_messages_user_platform_time", "user_id", "platform", "timestamp")
Index("ix_messages_user_contact_time", "user_id", "contact_id", "timestamp")
Index("ix_messages_user_unread", "user_id", "is_read", "timestamp")