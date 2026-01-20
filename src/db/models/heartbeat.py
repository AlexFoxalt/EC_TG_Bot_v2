from sqlalchemy import Column, DateTime, Integer, func, String

from src.db.models.base import Base


class Heartbeat(Base):
    __tablename__ = "heartbeat"
    __mapper_args__ = {"eager_defaults": True}

    id = Column(Integer, primary_key=True)

    timestamp = Column(DateTime(timezone=True), nullable=True)
    label = Column(String, index=True)

    date_created = Column(DateTime(timezone=True), server_default=func.now())
    date_updated = Column(DateTime(timezone=True), onupdate=func.now())
