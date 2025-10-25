"""
Bank API - User Model

User entity for authentication and authorization.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import String, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash

from app.models.base import BaseModel


class User(BaseModel):
    """
    User model for authentication and authorization.
    
    Attributes:
        email: Unique email address (used for login)
        password_hash: Hashed password
        role: User role (CUSTOMER, ADMIN, SUPER_ADMIN)
        is_active: Whether user account is active
        customer_id: Foreign key to customer (for CUSTOMER role)
    """
    
    __tablename__ = 'users'
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    # Authorization
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='CUSTOMER',
        index=True
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    
    # Foreign Keys (nullable for admin users)
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('customers.id', ondelete='CASCADE'),
        nullable=True,
        unique=True
    )
    
    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="user"
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('CUSTOMER', 'ADMIN', 'SUPER_ADMIN')",
            name='chk_user_role'
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def set_password(self, password: str) -> None:
        """
        Set user password (hashed).
        
        Args:
            password: Plain text password
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """
        Check if provided password matches stored hash.
        
        Args:
            password: Plain text password to check
            
        Returns:
            True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_customer(self) -> bool:
        """Check if user is a customer."""
        return self.role == 'CUSTOMER'
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role in ('ADMIN', 'SUPER_ADMIN')
    
    @property
    def is_super_admin(self) -> bool:
        """Check if user is a super admin."""
        return self.role == 'SUPER_ADMIN'
    
    def has_role(self, *roles: str) -> bool:
        """
        Check if user has one of the specified roles.
        
        Args:
            roles: Role names to check
            
        Returns:
            True if user has one of the roles
        """
        return self.role in roles

