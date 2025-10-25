"""
Bank API - Schemas Package

Pydantic schemas for request validation and response serialization.
"""

from app.schemas.customer import (
    CustomerCreateRequest,
    CustomerUpdateRequest,
    CustomerResponse
)
from app.schemas.account import (
    AccountCreateRequest,
    AccountResponse,
    AccountBalanceResponse
)
from app.schemas.transaction import (
    DepositRequest,
    WithdrawalRequest,
    TransactionResponse,
    TransactionListResponse
)
from app.schemas.loan import (
    LoanApplicationRequest,
    LoanApplicationResponse,
    LoanReviewRequest,
    LoanDisbursementRequest
)
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenRefreshRequest,
    UserResponse
)

__all__ = [
    # Customer
    'CustomerCreateRequest',
    'CustomerUpdateRequest',
    'CustomerResponse',
    # Account
    'AccountCreateRequest',
    'AccountResponse',
    'AccountBalanceResponse',
    # Transaction
    'DepositRequest',
    'WithdrawalRequest',
    'TransactionResponse',
    'TransactionListResponse',
    # Loan
    'LoanApplicationRequest',
    'LoanApplicationResponse',
    'LoanReviewRequest',
    'LoanDisbursementRequest',
    # Auth
    'LoginRequest',
    'LoginResponse',
    'RegisterRequest',
    'TokenRefreshRequest',
    'UserResponse',
]

