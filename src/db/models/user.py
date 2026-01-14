from sqlalchemy import Column, String, Boolean, BigInteger
from sqlalchemy import DateTime
from sqlalchemy import func

from src.db.models.base import Base


class User(Base):
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    id = Column(BigInteger, primary_key=True)

    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    is_bot = Column(Boolean, default=False)
    language_code = Column(String, nullable=True)
    id_admin = Column(Boolean, default=False)
    notifs_enabled = Column(Boolean, default=True)
    night_notif_sound_enabled = Column(Boolean, default=True)

    date_created = Column(DateTime(timezone=True), server_default=func.now())
    date_updated = Column(DateTime(timezone=True), onupdate=func.now())
