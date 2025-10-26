"""
Centralized Marshmallow Schema Registry

This module provides a single source of truth for all Marshmallow schemas
used in Flask-SMOREST API documentation and validation.

All Pydantic models are converted to Marshmallow schemas here, ensuring:
- Single conversion point (DRY)
- Easy to locate schemas
- Reusable across blueprints
- Consistent naming

Usage:
    from app.api.schemas import LoginSchema, TokenResponseSchema
    
    @auth_bp.arguments(LoginSchema)
    @auth_bp.response(200, TokenResponseSchema)
    def login(args):
        pass
"""

from marshmallow import Schema, fields
from app.api.schema_bridge import pydantic_to_marshmallow, create_response_schema

# ============================================================================
# Import Pydantic Models
# ============================================================================

# Auth schemas
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    PasswordChangeRequest
)

# Customer schemas
from app.schemas.customer import (
    CustomerCreateRequest,
    CustomerUpdateRequest
)

# Account schemas
from app.schemas.account import AccountCreateRequest

# Transaction schemas
from app.schemas.transaction import (
    DepositRequest,
    WithdrawalRequest
)

# Loan schemas
from app.schemas.loan import (
    LoanApplicationRequest,
    LoanReviewRequest
)


# ============================================================================
# REQUEST SCHEMAS (from Pydantic)
# ============================================================================

# Auth
LoginSchema = pydantic_to_marshmallow(LoginRequest)
RegisterSchema = pydantic_to_marshmallow(RegisterRequest)
PasswordChangeSchema = pydantic_to_marshmallow(PasswordChangeRequest)

# Customer
CustomerCreateSchema = pydantic_to_marshmallow(CustomerCreateRequest)
CustomerUpdateSchema = pydantic_to_marshmallow(CustomerUpdateRequest)

# Account
AccountCreateSchema = pydantic_to_marshmallow(AccountCreateRequest)

# Transaction
DepositSchema = pydantic_to_marshmallow(DepositRequest)
WithdrawalSchema = pydantic_to_marshmallow(WithdrawalRequest)

# Loan
LoanApplicationSchema = pydantic_to_marshmallow(LoanApplicationRequest)
LoanReviewSchema = pydantic_to_marshmallow(LoanReviewRequest)


# ============================================================================
# RESPONSE SCHEMAS (reusable)
# ============================================================================

# Auth responses
TokenResponseSchema = create_response_schema(
    'TokenResponse',
    {
        'access_token': fields.String(required=True, metadata={
            'description': 'JWT access token',
            'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        }),
        'refresh_token': fields.String(required=True, metadata={
            'description': 'JWT refresh token',
            'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        }),
        'token_type': fields.String(required=True, metadata={
            'description': 'Token type',
            'example': 'bearer'
        }),
        'expires_in': fields.Integer(required=True, metadata={
            'description': 'Token expiration time in seconds',
            'example': 3600
        })
    }
)

UserInfoSchema = create_response_schema(
    'UserInfo',
    {
        'id': fields.UUID(required=True),
        'email': fields.String(required=True),
        'role': fields.String(required=True, metadata={
            'description': 'User role',
            'example': 'CUSTOMER',
            'enum': ['CUSTOMER', 'ADMIN', 'SUPER_ADMIN']
        }),
        'is_active': fields.Boolean(required=True),
        'customer_id': fields.UUID(allow_none=True),
        'created_at': fields.DateTime(required=True)
    }
)

# Customer responses
CustomerResponseSchema = create_response_schema(
    'CustomerResponse',
    {
        'id': fields.UUID(required=True),
        'email': fields.String(required=True),
        'first_name': fields.String(required=True),
        'last_name': fields.String(required=True),
        'status': fields.String(required=True, metadata={
            'enum': ['ACTIVE', 'SUSPENDED', 'CLOSED']
        }),
        'created_at': fields.DateTime(required=False)
    }
)

# Account responses
AccountResponseSchema = create_response_schema(
    'AccountResponse',
    {
        'id': fields.UUID(required=True),
        'customer_id': fields.UUID(required=True),
        'account_type': fields.String(required=True, metadata={
            'enum': ['CHECKING', 'LOAN']
        }),
        'account_number': fields.String(required=True),
        'status': fields.String(required=True, metadata={
            'enum': ['ACTIVE', 'CLOSED']
        }),
        'balance': fields.String(required=True, metadata={
            'description': 'Account balance (Decimal as string)'
        }),
        'currency': fields.String(required=True, metadata={
            'example': 'USD'
        })
    }
)

BalanceResponseSchema = create_response_schema(
    'BalanceResponse',
    {
        'account_id': fields.UUID(required=True),
        'account_number': fields.String(required=True),
        'balance': fields.String(required=True),
        'currency': fields.String(required=True),
        'status': fields.String(required=True),
        'as_of': fields.DateTime(required=True)
    }
)

# Transaction responses
TransactionResponseSchema = create_response_schema(
    'TransactionResponse',
    {
        'id': fields.UUID(required=True),
        'account_id': fields.UUID(required=True),
        'transaction_type': fields.String(required=True, metadata={
            'enum': ['DEPOSIT', 'WITHDRAWAL', 'LOAN_DISBURSEMENT']
        }),
        'amount': fields.String(required=True),
        'balance_after': fields.String(required=True),
        'reference_number': fields.String(required=True),
        'status': fields.String(required=True, metadata={
            'enum': ['PENDING', 'COMPLETED', 'FAILED', 'REVERSED']
        }),
        'created_at': fields.DateTime(required=False)
    }
)

# Loan responses
LoanResponseSchema = create_response_schema(
    'LoanResponse',
    {
        'id': fields.UUID(required=True),
        'customer_id': fields.UUID(required=True),
        'application_number': fields.String(required=True),
        'requested_amount': fields.String(required=True),
        'status': fields.String(required=True, metadata={
            'enum': ['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'DISBURSED']
        }),
        'applied_at': fields.DateTime(required=True),
        'reviewed_at': fields.DateTime(required=False),
        'approved_amount': fields.String(required=False),
        'interest_rate': fields.String(required=False)
    }
)

# Generic responses
MessageSchema = create_response_schema(
    'Message',
    {
        'message': fields.String(required=True, metadata={
            'example': 'Operation successful'
        })
    }
)

AdminActionResponseSchema = create_response_schema(
    'AdminActionResponse',
    {
        'message': fields.String(required=True),
        'id': fields.UUID(required=True),
        'status': fields.String(required=True)
    }
)


# ============================================================================
# LIST & PAGINATION SCHEMAS
# ============================================================================

class PaginationSchema(Schema):
    """Pagination metadata."""
    total = fields.Integer(required=True, metadata={'description': 'Total number of items'})
    limit = fields.Integer(required=True, metadata={'description': 'Items per page'})
    offset = fields.Integer(required=True, metadata={'description': 'Offset from start'})


class AccountListSchema(Schema):
    """List of accounts with data."""
    data = fields.List(fields.Dict(), required=True, metadata={
        'description': 'List of account objects'
    })


class TransactionListSchema(Schema):
    """List of transactions with pagination."""
    data = fields.List(fields.Dict(), required=True)
    pagination = fields.Nested(PaginationSchema, required=True)


class LoanListSchema(Schema):
    """List of loan applications with pagination."""
    data = fields.List(fields.Dict(), required=True)
    pagination = fields.Nested(PaginationSchema, required=True)


class CustomerListSchema(Schema):
    """List of customers with pagination."""
    data = fields.List(fields.Dict(), required=True)
    pagination = fields.Nested(PaginationSchema, required=True)


# ============================================================================
# QUERY PARAMETER SCHEMAS
# ============================================================================

class TransactionFilterSchema(Schema):
    """Query parameters for transaction filtering."""
    start_date = fields.Date(
        required=False,
        metadata={'description': 'Filter transactions from this date'}
    )
    end_date = fields.Date(
        required=False,
        metadata={'description': 'Filter transactions until this date'}
    )
    transaction_type = fields.String(
        required=False,
        metadata={
            'description': 'Filter by transaction type',
            'enum': ['DEPOSIT', 'WITHDRAWAL', 'LOAN_DISBURSEMENT']
        }
    )
    limit = fields.Integer(
        load_default=50,
        metadata={'description': 'Number of items per page'}
    )
    offset = fields.Integer(
        load_default=0,
        metadata={'description': 'Offset from start'}
    )


class LoanFilterSchema(Schema):
    """Query parameters for loan filtering."""
    status = fields.String(
        required=False,
        metadata={
            'description': 'Filter by loan status',
            'enum': ['PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'DISBURSED']
        }
    )
    limit = fields.Integer(load_default=20)
    offset = fields.Integer(load_default=0)


class CustomerFilterSchema(Schema):
    """Query parameters for customer filtering."""
    status = fields.String(
        required=False,
        metadata={
            'description': 'Filter by customer status',
            'enum': ['ACTIVE', 'SUSPENDED', 'CLOSED']
        }
    )
    limit = fields.Integer(load_default=50)
    offset = fields.Integer(load_default=0)


class ReasonSchema(Schema):
    """Optional reason field for admin actions."""
    reason = fields.String(
        required=False,
        metadata={'description': 'Reason for the action'}
    )


# ============================================================================
# SCHEMA REGISTRY (for easy lookup)
# ============================================================================

# All schemas in one place for easy reference
SCHEMAS = {
    # Request schemas
    'LoginSchema': LoginSchema,
    'RegisterSchema': RegisterSchema,
    'PasswordChangeSchema': PasswordChangeSchema,
    'CustomerCreateSchema': CustomerCreateSchema,
    'CustomerUpdateSchema': CustomerUpdateSchema,
    'AccountCreateSchema': AccountCreateSchema,
    'DepositSchema': DepositSchema,
    'WithdrawalSchema': WithdrawalSchema,
    'LoanApplicationSchema': LoanApplicationSchema,
    'LoanReviewSchema': LoanReviewSchema,
    
    # Response schemas
    'TokenResponseSchema': TokenResponseSchema,
    'UserInfoSchema': UserInfoSchema,
    'CustomerResponseSchema': CustomerResponseSchema,
    'AccountResponseSchema': AccountResponseSchema,
    'BalanceResponseSchema': BalanceResponseSchema,
    'TransactionResponseSchema': TransactionResponseSchema,
    'LoanResponseSchema': LoanResponseSchema,
    'MessageSchema': MessageSchema,
    'AdminActionResponseSchema': AdminActionResponseSchema,
    
    # List schemas
    'AccountListSchema': AccountListSchema,
    'TransactionListSchema': TransactionListSchema,
    'LoanListSchema': LoanListSchema,
    'CustomerListSchema': CustomerListSchema,
    
    # Filter schemas
    'TransactionFilterSchema': TransactionFilterSchema,
    'LoanFilterSchema': LoanFilterSchema,
    'CustomerFilterSchema': CustomerFilterSchema,
    'ReasonSchema': ReasonSchema,
}


def get_schema(name: str) -> Schema:
    """
    Get schema by name from registry.
    
    Args:
        name: Schema name (e.g., 'LoginSchema')
        
    Returns:
        Marshmallow Schema class
        
    Raises:
        KeyError: If schema not found
        
    Example:
        schema = get_schema('LoginSchema')
    """
    if name not in SCHEMAS:
        raise KeyError(f"Schema '{name}' not found in registry. Available: {list(SCHEMAS.keys())}")
    return SCHEMAS[name]

