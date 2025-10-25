"""
Bank API - Transaction Schemas

Pydantic schemas for transaction-related requests and responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    """Schema for deposit transaction request."""
    amount: Decimal = Field(..., gt=0, description="Deposit amount")
    currency: str = Field(default='USD', pattern=r'^[A-Z]{3}$', description="Currency code")
    description: Optional[str] = Field(None, max_length=500, description="Transaction description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "amount": 500.00,
                "currency": "USD",
                "description": "Paycheck deposit"
            }
        }
    }


class WithdrawalRequest(BaseModel):
    """Schema for withdrawal transaction request."""
    amount: Decimal = Field(..., gt=0, description="Withdrawal amount")
    currency: str = Field(default='USD', pattern=r'^[A-Z]{3}$', description="Currency code")
    description: Optional[str] = Field(None, max_length=500, description="Transaction description")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "amount": 200.00,
                "currency": "USD",
                "description": "ATM withdrawal"
            }
        }
    }


class TransactionResponse(BaseModel):
    """Schema for transaction response."""
    id: UUID = Field(..., description="Transaction ID")
    account_id: UUID = Field(..., description="Account ID")
    transaction_type: str = Field(..., description="Transaction type")
    amount: Decimal = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    balance_after: Decimal = Field(..., description="Balance after transaction")
    description: Optional[str] = Field(None, description="Transaction description")
    reference_number: str = Field(..., description="Unique reference number")
    status: str = Field(..., description="Transaction status")
    created_at: datetime = Field(..., description="Transaction creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "750e8400-e29b-41d4-a716-446655440002",
                "account_id": "650e8400-e29b-41d4-a716-446655440001",
                "transaction_type": "DEPOSIT",
                "amount": 500.00,
                "currency": "USD",
                "balance_after": 1500.00,
                "description": "Paycheck deposit",
                "reference_number": "TXN-20251025-000001",
                "status": "COMPLETED",
                "created_at": "2025-10-25T11:00:00Z",
                "processed_at": "2025-10-25T11:00:01Z"
            }
        }
    }


class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list response."""
    data: List[TransactionResponse] = Field(..., description="List of transactions")
    pagination: "PaginationMetadata" = Field(..., description="Pagination information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "id": "750e8400-e29b-41d4-a716-446655440002",
                        "account_id": "650e8400-e29b-41d4-a716-446655440001",
                        "transaction_type": "DEPOSIT",
                        "amount": 500.00,
                        "currency": "USD",
                        "balance_after": 1500.00,
                        "description": "Paycheck deposit",
                        "reference_number": "TXN-20251025-000001",
                        "status": "COMPLETED",
                        "created_at": "2025-10-25T11:00:00Z",
                        "processed_at": "2025-10-25T11:00:01Z"
                    }
                ],
                "pagination": {
                    "total": 50,
                    "limit": 20,
                    "offset": 0,
                    "has_more": True
                }
            }
        }
    }


class PaginationMetadata(BaseModel):
    """Schema for pagination metadata."""
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Offset from start")
    has_more: bool = Field(..., description="Whether more items exist")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 50,
                "limit": 20,
                "offset": 0,
                "has_more": True
            }
        }
    }


class TransactionFilterParams(BaseModel):
    """Schema for transaction filtering parameters."""
    start_date: Optional[datetime] = Field(None, description="Filter transactions from this date")
    end_date: Optional[datetime] = Field(None, description="Filter transactions until this date")
    transaction_type: Optional[str] = Field(None, description="Filter by transaction type")
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items per page")
    offset: int = Field(default=0, ge=0, description="Offset from start")

