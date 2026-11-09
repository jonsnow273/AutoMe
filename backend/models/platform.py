from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, Index, UniqueConstraint
from sqlalchemy.sql import func
from backend.database import Base
import enum


class PlatformType(str, enum.Enum):
    DISCORD = "discord"
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    platform_type = Column(SQLEnum(PlatformType), nullable=False, index=True)

    # Encrypted credentials (Fernet) — JSON string:
    # Discord: {"bot_token": "..."}
    # WhatsApp: {"session_data": "..."} (base64 encoded)
    # Instagram: {"username": "...", "password": "..."}
    credentials = Column(Text, nullable=False)

    is_connected = Column(Boolean, default=False, nullable=False)
    connected_at = Column(DateTime(timezone=True), nullable=True)

    # Platform-specific settings (JSON)
    # Discord: {"auto_reply_enabled": true, "dm_only": true}
    # WhatsApp: {"auto_reply_enabled": true}
    # Instagram: {"auto_reply_enabled": true}
    settings = Column(Text, nullable=True)  # JSON string

    last_sync = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "platform_type", name="uq_user_platform"),
        Index("ix_platforms_user_connected", "user_id", "is_connected"),
    )