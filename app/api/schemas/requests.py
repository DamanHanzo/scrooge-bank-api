"""
Request Schemas

All Marshmallow schemas for API request validation.
These schemas are converted from Pydantic models.
"""

from app.api.schema_bridge import pydantic_to_marshmallow

# Import Pydantic Models
from app.schemas.auth import LoginRequest, RegisterRequest, PasswordChangeRequest
from app.schemas.customer import CustomerCreateRequest, CustomerUpdateRequest, CustomerStatusUpdateRequest
from app.schemas.account import AccountCreateRequest, AccountStatusUpdateRequest
from app.schemas.transaction import (
    TransactionCreateRequest,
    DepositRequest,
    WithdrawalRequest
)
from app.schemas.loan import (
    LoanApplicationRequest,
    LoanReviewRequest,
    LoanPaymentRequest,
    LoanApplicationStatusUpdateRequest
)


# ============================================================================
# AUTH REQUEST SCHEMAS
# ============================================================================

LoginSchema = pydantic_to_marshmallow(LoginRequest)
RegisterSchema = pydantic_to_marshmallow(RegisterRequest)
PasswordChangeSchema = pydantic_to_marshmallow(PasswordChangeRequest)


# ============================================================================
# CUSTOMER REQUEST SCHEMAS
# ============================================================================

CustomerCreateSchema = pydantic_to_marshmallow(CustomerCreateRequest)
CustomerUpdateSchema = pydantic_to_marshmallow(CustomerUpdateRequest)
CustomerStatusUpdateSchema = pydantic_to_marshmallow(CustomerStatusUpdateRequest)


# ============================================================================
# ACCOUNT REQUEST SCHEMAS
# ============================================================================

AccountCreateSchema = pydantic_to_marshmallow(AccountCreateRequest)
AccountStatusUpdateSchema = pydantic_to_marshmallow(AccountStatusUpdateRequest)


# ============================================================================
# TRANSACTION REQUEST SCHEMAS
# ============================================================================

TransactionCreateSchema = pydantic_to_marshmallow(TransactionCreateRequest)
DepositSchema = pydantic_to_marshmallow(DepositRequest)
WithdrawalSchema = pydantic_to_marshmallow(WithdrawalRequest)


# ============================================================================
# LOAN REQUEST SCHEMAS
# ============================================================================

LoanApplicationSchema = pydantic_to_marshmallow(LoanApplicationRequest)
LoanReviewSchema = pydantic_to_marshmallow(LoanReviewRequest)
LoanPaymentSchema = pydantic_to_marshmallow(LoanPaymentRequest)
LoanApplicationStatusUpdateSchema = pydantic_to_marshmallow(LoanApplicationStatusUpdateRequest)
