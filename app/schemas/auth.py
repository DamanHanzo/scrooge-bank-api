"""
Bank API - Authentication Schemas

Pydantic schemas for authentication-related requests and responses.
"""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePassword123!"
            }
        }
    }


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user: "UserResponse" = Field(..., description="User information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "450e8400-e29b-41d4-a716-446655440005",
                    "email": "john.doe@example.com",
                    "role": "CUSTOMER",
                    "is_active": True,
                    "customer_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }
        }
    }


class RegisterRequest(BaseModel):
    """Schema for user registration request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    password_confirm: str = Field(..., min_length=8, description="Password confirmation")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @field_validator('password_confirm')
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        """Ensure password and confirmation match."""
        password = info.data.get('password')
        if password and v != password:
            raise ValueError('Passwords do not match')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!",
                "first_name": "John",
                "last_name": "Doe"
            }
        }
    }


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="JWT refresh token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
    }


class UserResponse(BaseModel):
    """Schema for user response."""
    id: UUID = Field(..., description="User ID")
    email: EmailStr = Field(..., description="Email address")
    role: Literal['CUSTOMER', 'ADMIN', 'SUPER_ADMIN'] = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    customer_id: Optional[UUID] = Field(None, description="Customer ID (for CUSTOMER role)")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "450e8400-e29b-41d4-a716-446655440005",
                "email": "john.doe@example.com",
                "role": "CUSTOMER",
                "is_active": True,
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-10-25T10:30:00Z"
            }
        }
    }


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., min_length=8, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    new_password_confirm: str = Field(..., min_length=8, description="New password confirmation")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @field_validator('new_password_confirm')
    @classmethod
    def validate_passwords_match(cls, v: str, info) -> str:
        """Ensure new password and confirmation match."""
        new_password = info.data.get('new_password')
        if new_password and v != new_password:
            raise ValueError('Passwords do not match')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePassword123!",
                "new_password_confirm": "NewSecurePassword123!"
            }
        }
    }

