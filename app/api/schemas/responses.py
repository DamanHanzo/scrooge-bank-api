"""
Response Schemas

All Marshmallow schemas for API responses.
These define the structure of data returned from API endpoints.
"""

from marshmallow import fields
from app.api.schema_bridge import create_response_schema


# ============================================================================
# AUTH RESPONSE SCHEMAS
# ============================================================================

TokenResponseSchema = create_response_schema(
    "TokenResponse",
    {
        "access_token": fields.String(
            required=True,
            metadata={
                "description": "JWT access token",
                "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            },
        ),
        "refresh_token": fields.String(
            required=True,
            metadata={
                "description": "JWT refresh token",
                "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            },
        ),
        "token_type": fields.String(
            required=True, metadata={"description": "Token type", "example": "bearer"}
        ),
        "expires_in": fields.Integer(
            required=True,
            metadata={"description": "Token expiration time in seconds", "example": 3600},
        ),
    },
)

UserInfoSchema = create_response_schema(
    "UserInfo",
    {
        "id": fields.UUID(required=True),
        "email": fields.String(required=True),
        "role": fields.String(
            required=True,
            metadata={
                "description": "User role",
                "example": "CUSTOMER",
                "enum": ["CUSTOMER", "ADMIN", "SUPER_ADMIN"],
            },
        ),
        "is_active": fields.Boolean(required=True),
        "customer_id": fields.UUID(allow_none=True),
        "created_at": fields.DateTime(required=True),
    },
)


# ============================================================================
# CUSTOMER RESPONSE SCHEMAS
# ============================================================================

CustomerResponseSchema = create_response_schema(
    "CustomerResponse",
    {
        "id": fields.UUID(required=True),
        "email": fields.String(required=True),
        "first_name": fields.String(required=True),
        "last_name": fields.String(required=True),
        "status": fields.String(
            required=True, metadata={"enum": ["ACTIVE", "SUSPENDED", "CLOSED"]}
        ),
        "created_at": fields.DateTime(required=False),
    },
)


# ============================================================================
# ACCOUNT RESPONSE SCHEMAS
# ============================================================================

AccountResponseSchema = create_response_schema(
    "AccountResponse",
    {
        "id": fields.UUID(required=True),
        "customer_id": fields.UUID(required=True),
        "account_type": fields.String(required=True, metadata={"enum": ["CHECKING", "LOAN"]}),
        "account_number": fields.String(required=True),
        "status": fields.String(required=True, metadata={"enum": ["ACTIVE", "CLOSED"]}),
        "balance": fields.String(
            required=True, metadata={"description": "Account balance (Decimal as string)"}
        ),
        "currency": fields.String(required=True, metadata={"example": "USD"}),
    },
)

BalanceResponseSchema = create_response_schema(
    "BalanceResponse",
    {
        "account_id": fields.UUID(required=True),
        "account_number": fields.String(required=True),
        "balance": fields.String(required=True),
        "currency": fields.String(required=True),
        "status": fields.String(required=True),
        "as_of": fields.DateTime(required=True),
    },
)


# ============================================================================
# TRANSACTION RESPONSE SCHEMAS
# ============================================================================

TransactionResponseSchema = create_response_schema(
    "TransactionResponse",
    {
        "id": fields.UUID(required=True),
        "account_id": fields.UUID(required=True),
        "transaction_type": fields.String(
            required=True, metadata={"enum": ["DEPOSIT", "WITHDRAWAL", "LOAN_DISBURSEMENT"]}
        ),
        "amount": fields.String(required=True),
        "balance_after": fields.String(required=True),
        "reference_number": fields.String(required=True),
        "status": fields.String(
            required=True, metadata={"enum": ["PENDING", "COMPLETED", "FAILED", "REVERSED"]}
        ),
        "created_at": fields.DateTime(required=False),
    },
)


# ============================================================================
# LOAN RESPONSE SCHEMAS
# ============================================================================

LoanResponseSchema = create_response_schema(
    "LoanResponse",
    {
        "id": fields.UUID(required=True),
        "customer_id": fields.UUID(required=True),
        "application_number": fields.String(required=True),
        "requested_amount": fields.String(required=True),
        "status": fields.String(
            required=True,
            metadata={"enum": ["PENDING", "APPROVED", "REJECTED", "CANCELLED", "DISBURSED"]},
        ),
        "applied_at": fields.DateTime(required=True),
        "reviewed_at": fields.DateTime(required=False),
        "approved_amount": fields.String(required=False),
        "interest_rate": fields.String(required=False),
    },
)


# ============================================================================
# GENERIC RESPONSE SCHEMAS
# ============================================================================

MessageSchema = create_response_schema(
    "Message",
    {"message": fields.String(required=True, metadata={"example": "Operation successful"})},
)

AdminActionResponseSchema = create_response_schema(
    "AdminActionResponse",
    {
        "message": fields.String(required=True),
        "id": fields.UUID(required=True),
        "status": fields.String(required=True),
    },
)
