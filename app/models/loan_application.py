"""
Bank API - Loan Application Model

Loan application entity representing personal loan applications.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import String, Numeric, Integer, ForeignKey, CheckConstraint, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class LoanApplication(BaseModel):
    """
    Loan Application model representing personal loan applications.
    
    Attributes:
        customer_id: Foreign key to customer
        loan_account_id: Foreign key to loan account (after approval)
        application_number: Unique application identifier
        requested_amount: Amount requested by customer
        approved_amount: Amount approved (may differ from requested)
        interest_rate: Annual interest rate (decimal)
        term_months: Loan term in months
        purpose: Purpose of the loan
        employment_status: Customer's employment status
        annual_income: Customer's annual income
        status: Application status (PENDING, APPROVED, REJECTED, DISBURSED, CANCELLED)
        applied_at: When application was submitted
        reviewed_at: When application was reviewed
        disbursed_at: When loan was disbursed
        external_account_number: External account for disbursement
        external_routing_number: External routing number
        rejection_reason: Reason for rejection (if applicable)
        metadata: Additional application metadata (JSONB)
    """
    
    __tablename__ = 'loan_applications'
    
    # Foreign Keys
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('customers.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )
    
    loan_account_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('accounts.id', ondelete='RESTRICT'),
        nullable=True
    )
    
    # Application Information
    application_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )
    
    requested_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    approved_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True
    )
    
    interest_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="Annual interest rate as decimal (e.g., 0.0525 for 5.25%)"
    )
    
    term_months: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    purpose: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    # Customer Financial Information
    employment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    
    annual_income: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    
    # Status and Timestamps
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='PENDING',
        index=True
    )
    
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    disbursed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # External Account Information
    external_account_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )
    
    external_routing_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    
    # Rejection Information
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="loan_applications"
    )
    
    loan_account: Mapped[Optional["Account"]] = relationship(
        "Account",
        back_populates="loan_application"
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "requested_amount > 0",
            name='chk_requested_amount_positive'
        ),
        CheckConstraint(
            "(approved_amount IS NULL) OR (approved_amount > 0)",
            name='chk_approved_amount_positive'
        ),
        CheckConstraint(
            "(interest_rate IS NULL) OR (interest_rate >= 0)",
            name='chk_interest_rate_valid'
        ),
        CheckConstraint(
            "(term_months IS NULL) OR (term_months > 0)",
            name='chk_term_months_positive'
        ),
        CheckConstraint(
            "annual_income >= 0",
            name='chk_annual_income_valid'
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'DISBURSED', 'CANCELLED')",
            name='chk_loan_application_status'
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of LoanApplication."""
        return f"<LoanApplication(id={self.id}, number={self.application_number}, status={self.status}, amount={self.requested_amount})>"
    
    @property
    def is_pending(self) -> bool:
        """Check if application is pending."""
        return self.status == 'PENDING'
    
    @property
    def is_approved(self) -> bool:
        """Check if application is approved."""
        return self.status == 'APPROVED'
    
    @property
    def is_rejected(self) -> bool:
        """Check if application is rejected."""
        return self.status == 'REJECTED'
    
    @property
    def is_disbursed(self) -> bool:
        """Check if loan is disbursed."""
        return self.status == 'DISBURSED'
    
    @property
    def can_be_reviewed(self) -> bool:
        """Check if application can be reviewed."""
        return self.status == 'PENDING'
    
    @property
    def can_be_disbursed(self) -> bool:
        """Check if loan can be disbursed."""
        return self.status == 'APPROVED'

