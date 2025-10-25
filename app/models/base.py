"""
Bank API - Base Model

Base model class with common fields and functionality for all models.
"""

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import db


class BaseModel(db.Model):
    """
    Base model class that includes common fields for all models.
    
    Fields:
        - id: UUID primary key
        - created_at: Timestamp when record was created
        - updated_at: Timestamp when record was last updated
    """
    
    __abstract__ = True
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, '__str__'):
                value = str(value)
            result[column.name] = value
        return result
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"

