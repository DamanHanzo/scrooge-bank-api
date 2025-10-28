"""
Bank API - Loan Schemas

Pydantic schemas for loan-related requests and responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExternalAccountSchema(BaseModel):
    """Schema for external account information."""
    account_number: str = Field(..., min_length=4, max_length=50, description="External account number")
    routing_number: str = Field(..., pattern=r'^\d{9}$', description="Routing number (9 digits)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "account_number": "9876543210",
                "routing_number": "121000248"
            }
        }
    }


class LoanApplicationRequest(BaseModel):
    """Schema for submitting a loan application."""
    customer_id: UUID = Field(..., description="Customer ID")
    requested_amount: Decimal = Field(
        ...,
        gt=0,
        le=100000,
        description="Requested loan amount"
    )
    purpose: str = Field(..., min_length=1, max_length=100, description="Loan purpose")
    term_months: int = Field(..., ge=6, le=84, description="Loan term in months (6-84)")
    employment_status: Literal['FULL_TIME', 'PART_TIME', 'SELF_EMPLOYED', 'UNEMPLOYED', 'RETIRED'] = Field(
        ...,
        description="Employment status"
    )
    annual_income: Decimal = Field(..., ge=0, description="Annual income")
    external_account: ExternalAccountSchema = Field(..., description="External account for disbursement")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "requested_amount": 25000.00,
                "purpose": "Debt consolidation",
                "term_months": 36,
                "employment_status": "FULL_TIME",
                "annual_income": 75000.00,
                "external_account": {
                    "account_number": "9876543210",
                    "routing_number": "121000248"
                }
            }
        }
    }


class LoanReviewRequest(BaseModel):
    """Schema for reviewing a loan application (admin only)."""
    status: Literal['APPROVED', 'REJECTED'] = Field(..., description="Review decision")
    approved_amount: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Approved amount (if approved)"
    )
    interest_rate: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Interest rate as decimal (e.g., 0.0525 for 5.25%)"
    )
    term_months: Optional[int] = Field(None, ge=6, le=84, description="Approved term in months")
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "APPROVED",
                    "approved_amount": 25000.00,
                    "interest_rate": 0.0525,
                    "term_months": 36
                },
                {
                    "status": "REJECTED",
                    "rejection_reason": "Insufficient income for requested amount"
                }
            ]
        }
    }


class LoanDisbursementRequest(BaseModel):
    """Schema for disbursing an approved loan (admin only)."""
    confirm: bool = Field(..., description="Confirmation flag")
    notes: Optional[str] = Field(None, max_length=500, description="Disbursement notes")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "confirm": True,
                "notes": "Disbursement processed successfully"
            }
        }
    }


class LoanApplicationResponse(BaseModel):
    """Schema for loan application response."""
    id: UUID = Field(..., description="Application ID")
    customer_id: UUID = Field(..., description="Customer ID")
    loan_account_id: Optional[UUID] = Field(None, description="Loan account ID (after disbursement)")
    application_number: str = Field(..., description="Application number")
    requested_amount: Decimal = Field(..., description="Requested amount")
    approved_amount: Optional[Decimal] = Field(None, description="Approved amount")
    interest_rate: Optional[Decimal] = Field(None, description="Interest rate")
    term_months: Optional[int] = Field(None, description="Loan term in months")
    purpose: str = Field(..., description="Loan purpose")
    employment_status: str = Field(..., description="Employment status")
    annual_income: Decimal = Field(..., description="Annual income")
    status: str = Field(..., description="Application status")
    applied_at: datetime = Field(..., description="Application submission timestamp")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")
    disbursed_at: Optional[datetime] = Field(None, description="Disbursement timestamp")
    external_account: Optional[dict] = Field(None, description="External account info (masked)")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "950e8400-e29b-41d4-a716-446655440004",
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "loan_account_id": None,
                "application_number": "LOAN-20251025-000001",
                "requested_amount": 25000.00,
                "approved_amount": None,
                "interest_rate": None,
                "term_months": None,
                "purpose": "Debt consolidation",
                "employment_status": "FULL_TIME",
                "annual_income": 75000.00,
                "status": "PENDING",
                "applied_at": "2025-10-25T12:00:00Z",
                "reviewed_at": None,
                "disbursed_at": None,
                "external_account": {
                    "account_number": "***3210",
                    "routing_number": "121000248"
                },
                "rejection_reason": None
            }
        }
    }


class LoanApplicationStatusUpdateRequest(BaseModel):
    """Schema for updating loan application status."""
    status: Literal['CANCELLED', 'APPROVED', 'REJECTED'] = Field(..., description="New application status")
    approved_amount: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Approved amount (required if status is APPROVED)"
    )
    interest_rate: Optional[Decimal] = Field(
        None,
        ge=0,
        le=1,
        description="Interest rate as decimal (required if status is APPROVED)"
    )
    term_months: Optional[int] = Field(
        None,
        ge=6,
        le=84,
        description="Approved term in months (required if status is APPROVED)"
    )
    rejection_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for rejection (required if status is REJECTED)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "CANCELLED"
                },
                {
                    "status": "APPROVED",
                    "approved_amount": 25000.00,
                    "interest_rate": 0.0525,
                    "term_months": 36
                },
                {
                    "status": "REJECTED",
                    "rejection_reason": "Insufficient income for requested amount"
                }
            ]
        }
    }


class LoanPaymentRequest(BaseModel):
    """Schema for loan payment request."""

    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Payment amount (must be positive)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional payment description"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "amount": 1000.00,
                "description": "Monthly payment"
            }
        }
    }

