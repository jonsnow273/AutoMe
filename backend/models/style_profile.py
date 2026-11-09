from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from backend.database import Base


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Linguistic patterns
    avg_message_length = Column(Float, default=0.0)
    emoji_frequency = Column(Float, default=0.0)  # emojis per message
    preferred_emojis = Column(Text, nullable=True)  # JSON array of top emojis
    common_phrases = Column(Text, nullable=True)  # JSON array of frequent phrases/slang
    opener_patterns = Column(Text, nullable=True)  # JSON array of conversation openers
    closer_patterns = Column(Text, nullable=True)  # JSON array of conversation closers

    # Tone analysis
    tone = Column(String(20), default="casual")  # formal, casual, playful
    formality_score = Column(Float, default=0.5)  # 0-1 scale

    # Metadata
    sample_size = Column(Integer, default=0)  # Number of messages analyzed
    last_analyzed = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_style_profiles_user", "user_id"),
    )