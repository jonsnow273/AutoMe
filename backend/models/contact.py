from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


class RelationshipType(str, enum.Enum):
    FRIEND = "friend"
    ACQUAINTANCE = "acquaintance"
    STRANGER = "stranger"


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(String(20), nullable=False, index=True)  # discord, whatsapp, instagram
    platform_user_id = Column(String(100), nullable=False, index=True)  # Discord user ID, WA phone, IG pk

    username = Column(String(100), nullable=True)  # Discord username, IG handle
    display_name = Column(String(100), nullable=True)  # Discord display name, WA name, IG name
    avatar_url = Column(Text, nullable=True)

    relationship_type = Column(SQLEnum(RelationshipType), nullable=True, default=RelationshipType.STRANGER)
    last_interaction = Column(DateTime(timezone=True), nullable=True, index=True)

    # Style learning data (aggregated from messages)
    message_count = Column(Integer, default=0)
    avg_response_time_minutes = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Unique per user per platform
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "platform_user_id", name="uq_user_platform_contact"),
        Index("ix_contacts_user_platform", "user_id", "platform"),
        Index("ix_contacts_user_last_interaction", "user_id", "last_interaction"),
    )