"""
Bank API - Customer Model

Customer entity representing bank customers.
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import String, Date, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Customer(BaseModel):
    """
    Customer model representing a bank customer.
    
    Attributes:
        email: Unique email address
        first_name: Customer's first name
        last_name: Customer's last name
        date_of_birth: Customer's date of birth
        ssn_hash: Hashed Social Security Number
        phone: Contact phone number
        address_line_1: Primary address line
        address_line_2: Secondary address line (apt, suite, etc.)
        city: City
        state: State (2-letter code)
        zip_code: ZIP/Postal code
        status: Account status (ACTIVE, INACTIVE, SUSPENDED)
    """
    
    __tablename__ = 'customers'
    
    # Personal Information
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    date_of_birth: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )
    
    ssn_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Hashed SSN for security"
    )
    
    # Contact Information
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    
    # Address Information
    address_line_1: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    address_line_2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    state: Mapped[Optional[str]] = mapped_column(
        String(2),
        nullable=True
    )
    
    zip_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='ACTIVE',
        index=True
    )
    
    # Relationships
    accounts: Mapped[List["Account"]] = relationship(
        "Account",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    
    loan_applications: Mapped[List["LoanApplication"]] = relationship(
        "LoanApplication",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="customer",
        uselist=False
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')",
            name='chk_customer_status'
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of Customer."""
        return f"<Customer(id={self.id}, email={self.email}, status={self.status})>"
    
    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self) -> bool:
        """Check if customer is active."""
        return self.status == 'ACTIVE'

