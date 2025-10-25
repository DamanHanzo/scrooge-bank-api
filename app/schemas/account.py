"""
Bank API - Account Schemas

Pydantic schemas for account-related requests and responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AccountCreateRequest(BaseModel):
    """Schema for creating a new account."""
    customer_id: UUID = Field(..., description="Customer ID")
    account_type: Literal['CHECKING', 'LOAN'] = Field(..., description="Account type")
    initial_deposit: Optional[Decimal] = Field(
        None,
        ge=0,
        decimal_places=2,
        description="Initial deposit amount (for checking accounts)"
    )
    currency: str = Field(default='USD', pattern=r'^[A-Z]{3}$', description="Currency code")
    
    @field_validator('initial_deposit')
    @classmethod
    def validate_initial_deposit(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Validate initial deposit is only for checking accounts."""
        account_type = info.data.get('account_type')
        if account_type == 'LOAN' and v is not None:
            raise ValueError('Loan accounts cannot have an initial deposit')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_type": "CHECKING",
                "initial_deposit": 1000.00,
                "currency": "USD"
            }
        }
    }


class AccountResponse(BaseModel):
    """Schema for account response."""
    id: UUID = Field(..., description="Account ID")
    customer_id: UUID = Field(..., description="Customer ID")
    account_type: str = Field(..., description="Account type")
    account_number: str = Field(..., description="Account number")
    status: str = Field(..., description="Account status")
    balance: Decimal = Field(..., description="Current balance")
    currency: str = Field(..., description="Currency code")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "account_type": "CHECKING",
                "account_number": "CHK-1234567890",
                "status": "ACTIVE",
                "balance": 1000.00,
                "currency": "USD",
                "created_at": "2025-10-25T10:35:00Z",
                "updated_at": "2025-10-25T10:35:00Z"
            }
        }
    }


class AccountBalanceResponse(BaseModel):
    """Schema for account balance response."""
    account_id: UUID = Field(..., description="Account ID")
    account_number: str = Field(..., description="Account number")
    balance: Decimal = Field(..., description="Current balance")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Account status")
    as_of: datetime = Field(..., description="Balance as of timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "account_id": "650e8400-e29b-41d4-a716-446655440001",
                "account_number": "CHK-1234567890",
                "balance": 1500.00,
                "currency": "USD",
                "status": "ACTIVE",
                "as_of": "2025-10-25T12:00:00Z"
            }
        }
    }


class AccountStatusUpdateRequest(BaseModel):
    """Schema for updating account status."""
    status: Literal['ACTIVE', 'CLOSED', 'FROZEN'] = Field(..., description="New account status")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for status change")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "FROZEN",
                "reason": "Suspected fraudulent activity"
            }
        }
    }

