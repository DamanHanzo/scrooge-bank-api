"""
Bank API - Customer Schemas

Pydantic schemas for customer-related requests and responses.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class AddressSchema(BaseModel):
    """Address information schema."""
    line_1: str = Field(..., min_length=1, max_length=255, description="Address line 1")
    line_2: Optional[str] = Field(None, max_length=255, description="Address line 2")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str = Field(..., min_length=2, max_length=2, description="State (2-letter code)")
    zip_code: str = Field(..., pattern=r'^\d{5}(-\d{4})?$', description="ZIP code")
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Ensure state code is uppercase."""
        return v.upper()


class CustomerCreateRequest(BaseModel):
    """Schema for creating a new customer."""
    email: EmailStr = Field(..., description="Customer email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    date_of_birth: date = Field(..., description="Date of birth (YYYY-MM-DD)")
    ssn: str = Field(..., pattern=r'^\d{3}-\d{2}-\d{4}$', description="SSN (XXX-XX-XXXX)")
    phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{10,15}$', description="Phone number")
    address: Optional[AddressSchema] = Field(None, description="Address information")
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_age(cls, v: date) -> date:
        """Ensure customer is at least 18 years old."""
        from datetime import date as date_type
        today = date_type.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('Customer must be at least 18 years old')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
                "ssn": "123-45-6789",
                "phone": "+15550123",
                "address": {
                    "line_1": "123 Main St",
                    "line_2": "Apt 4B",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip_code": "94102"
                }
            }
        }
    }


class CustomerUpdateRequest(BaseModel):
    """Schema for updating customer information."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{10,15}$')
    address: Optional[AddressSchema] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "phone": "+15550199",
                "address": {
                    "line_1": "456 Oak Ave",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip_code": "94105"
                }
            }
        }
    }


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    id: UUID = Field(..., description="Customer ID")
    email: EmailStr = Field(..., description="Email address")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    date_of_birth: date = Field(..., description="Date of birth")
    phone: Optional[str] = Field(None, description="Phone number")
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    status: str = Field(..., description="Customer status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-05-15",
                "phone": "+15550123",
                "address_line_1": "123 Main St",
                "address_line_2": "Apt 4B",
                "city": "San Francisco",
                "state": "CA",
                "zip_code": "94102",
                "status": "ACTIVE",
                "created_at": "2025-10-25T10:30:00Z",
                "updated_at": "2025-10-25T10:30:00Z"
            }
        }
    }

