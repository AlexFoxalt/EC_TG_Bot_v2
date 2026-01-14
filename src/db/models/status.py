from sqlalchemy import Column, Boolean
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import func

from src.db.models.base import Base


class Status(Base):
    __tablename__ = "statuses"
    __mapper_args__ = {"eager_defaults": True}

    id = Column(Integer, primary_key=True)

    value = Column(Boolean)

    date_created = Column(DateTime(timezone=True), server_default=func.now())
