"""
Bank API - Account Model

Account entity representing checking and loan accounts.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import String, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Account(BaseModel):
    """
    Account model representing checking or loan accounts.
    
    Attributes:
        customer_id: Foreign key to customer
        account_type: Type of account (CHECKING, LOAN)
        account_number: Unique account number
        status: Account status (ACTIVE, CLOSED, FROZEN)
        balance: Current account balance
        currency: Currency code (default USD)
    """
    
    __tablename__ = 'accounts'
    
    # Foreign Keys
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('customers.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )
    
    # Account Information
    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    
    account_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='ACTIVE',
        index=True
    )
    
    balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal('0.00')
    )
    
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default='USD'
    )
    
    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="accounts"
    )
    
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="Transaction.created_at.desc()"
    )
    
    loan_application: Mapped[Optional["LoanApplication"]] = relationship(
        "LoanApplication",
        back_populates="loan_account",
        uselist=False
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('CHECKING', 'LOAN')",
            name='chk_account_type'
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'CLOSED', 'FROZEN')",
            name='chk_account_status'
        ),
        CheckConstraint(
            "(account_type != 'CHECKING') OR (balance >= 0)",
            name='chk_balance_checking'
        ),
        CheckConstraint(
            "(account_type != 'LOAN') OR (balance <= 0)",
            name='chk_balance_loan'
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of Account."""
        return f"<Account(id={self.id}, number={self.account_number}, type={self.account_type}, balance={self.balance})>"
    
    @property
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == 'ACTIVE'
    
    @property
    def is_frozen(self) -> bool:
        """Check if account is frozen."""
        return self.status == 'FROZEN'
    
    @property
    def is_checking(self) -> bool:
        """Check if account is a checking account."""
        return self.account_type == 'CHECKING'
    
    @property
    def is_loan(self) -> bool:
        """Check if account is a loan account."""
        return self.account_type == 'LOAN'
    
    def can_transact(self) -> bool:
        """Check if account can perform transactions."""
        return self.status == 'ACTIVE'

