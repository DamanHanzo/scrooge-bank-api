"""
Bank API - Transaction Model

Transaction entity representing account transactions.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import String, Numeric, ForeignKey, CheckConstraint, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Transaction(BaseModel):
    """
    Transaction model representing account transactions.
    
    Attributes:
        account_id: Foreign key to account
        transaction_type: Type of transaction (DEPOSIT, WITHDRAWAL, LOAN_DISBURSEMENT)
        amount: Transaction amount (always positive)
        currency: Currency code
        balance_after: Account balance after transaction
        description: Transaction description
        reference_number: Unique transaction reference
        status: Transaction status (PENDING, COMPLETED, FAILED, REVERSED)
        processed_at: When transaction was processed
        metadata: Additional transaction metadata (JSONB)
    """
    
    __tablename__ = 'transactions'
    
    # Foreign Keys
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('accounts.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )
    
    # Transaction Information
    transaction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )
    
    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default='USD'
    )
    
    balance_after: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    reference_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='PENDING',
        index=True
    )
    
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="transactions"
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name='chk_amount_positive'
        ),
        CheckConstraint(
            "transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'LOAN_DISBURSEMENT')",
            name='chk_transaction_type'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'FAILED', 'REVERSED')",
            name='chk_transaction_status'
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of Transaction."""
        return f"<Transaction(id={self.id}, type={self.transaction_type}, amount={self.amount}, status={self.status})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if transaction is completed."""
        return self.status == 'COMPLETED'
    
    @property
    def is_pending(self) -> bool:
        """Check if transaction is pending."""
        return self.status == 'PENDING'
    
    @property
    def is_reversed(self) -> bool:
        """Check if transaction is reversed."""
        return self.status == 'REVERSED'
    
    @property
    def is_deposit(self) -> bool:
        """Check if transaction is a deposit."""
        return self.transaction_type == 'DEPOSIT'
    
    @property
    def is_withdrawal(self) -> bool:
        """Check if transaction is a withdrawal."""
        return self.transaction_type == 'WITHDRAWAL'

