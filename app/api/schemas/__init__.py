"""
Marshmallow Schema Package

A cleaner, more maintainable structure for all API schemas.

Structure:
- requests.py: All request/input schemas
- responses.py: All response/output schemas
- filters.py: Query parameter and filter schemas
- lists.py: List and pagination schemas
- admin.py: Admin/bank operator schemas

Usage:
    from app.api.schemas import LoginSchema, TokenResponseSchema
"""

from marshmallow import Schema

# Request schemas
from app.api.schemas.requests import (
    LoginSchema,
    RegisterSchema,
    PasswordChangeSchema,
    CustomerCreateSchema,
    CustomerUpdateSchema,
    CustomerStatusUpdateSchema,
    AccountCreateSchema,
    AccountStatusUpdateSchema,
    TransactionCreateSchema,
    DepositSchema,
    WithdrawalSchema,
    LoanApplicationSchema,
    LoanReviewSchema,
    LoanPaymentSchema,
    LoanApplicationStatusUpdateSchema,
)

# Response schemas
from app.api.schemas.responses import (
    TokenResponseSchema,
    UserInfoSchema,
    CustomerResponseSchema,
    AccountResponseSchema,
    BalanceResponseSchema,
    TransactionResponseSchema,
    LoanResponseSchema,
    MessageSchema,
    AdminActionResponseSchema,
    # Error schemas
    ErrorResponseSchema,
    ErrorDetailSchema,
    ValidationErrorSchema,
    AuthenticationErrorSchema,
    AuthorizationErrorSchema,
    NotFoundErrorSchema,
    BusinessRuleErrorSchema,
)

# Filter schemas
from app.api.schemas.filters import (
    AccountFilterSchema,
    TransactionFilterSchema,
    LoanFilterSchema,
    CustomerFilterSchema,
    ReasonSchema,
)

# List schemas
from app.api.schemas.lists import (
    PaginationSchema,
    AccountListItemSchema,
    AccountListSchema,
    TransactionListSchema,
    LoanListSchema,
    CustomerListSchema,
)

# Admin schemas
from app.api.schemas.admin import (
    AccountBreakdownSchema,
    BankFinancialStatusSchema,
)


# ============================================================================
# SCHEMA REGISTRY (for easy lookup)
# ============================================================================

# All schemas in one place for easy reference
SCHEMAS = {
    # Request schemas
    "LoginSchema": LoginSchema,
    "RegisterSchema": RegisterSchema,
    "PasswordChangeSchema": PasswordChangeSchema,
    "CustomerCreateSchema": CustomerCreateSchema,
    "CustomerUpdateSchema": CustomerUpdateSchema,
    "CustomerStatusUpdateSchema": CustomerStatusUpdateSchema,
    "AccountCreateSchema": AccountCreateSchema,
    "AccountStatusUpdateSchema": AccountStatusUpdateSchema,
    "TransactionCreateSchema": TransactionCreateSchema,
    "DepositSchema": DepositSchema,
    "WithdrawalSchema": WithdrawalSchema,
    "LoanApplicationSchema": LoanApplicationSchema,
    "LoanReviewSchema": LoanReviewSchema,
    "LoanPaymentSchema": LoanPaymentSchema,
    "LoanApplicationStatusUpdateSchema": LoanApplicationStatusUpdateSchema,
    # Response schemas
    "TokenResponseSchema": TokenResponseSchema,
    "UserInfoSchema": UserInfoSchema,
    "CustomerResponseSchema": CustomerResponseSchema,
    "AccountResponseSchema": AccountResponseSchema,
    "BalanceResponseSchema": BalanceResponseSchema,
    "TransactionResponseSchema": TransactionResponseSchema,
    "LoanResponseSchema": LoanResponseSchema,
    "MessageSchema": MessageSchema,
    "AdminActionResponseSchema": AdminActionResponseSchema,
    "AccountBreakdownSchema": AccountBreakdownSchema,
    "BankFinancialStatusSchema": BankFinancialStatusSchema,
    # List schemas
    "AccountListSchema": AccountListSchema,
    "TransactionListSchema": TransactionListSchema,
    "LoanListSchema": LoanListSchema,
    "CustomerListSchema": CustomerListSchema,
    # Filter schemas
    "AccountFilterSchema": AccountFilterSchema,
    "TransactionFilterSchema": TransactionFilterSchema,
    "LoanFilterSchema": LoanFilterSchema,
    "CustomerFilterSchema": CustomerFilterSchema,
    "ReasonSchema": ReasonSchema,
    # Item schemas
    "AccountListItemSchema": AccountListItemSchema,
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


# Export all for backward compatibility
__all__ = [
    # Request schemas
    "LoginSchema",
    "RegisterSchema",
    "PasswordChangeSchema",
    "CustomerCreateSchema",
    "CustomerUpdateSchema",
    "AccountCreateSchema",
    "AccountStatusUpdateSchema",
    "TransactionCreateSchema",
    "DepositSchema",
    "WithdrawalSchema",
    "LoanApplicationSchema",
    "LoanReviewSchema",
    "LoanPaymentSchema",
    # Response schemas
    "TokenResponseSchema",
    "UserInfoSchema",
    "CustomerResponseSchema",
    "AccountResponseSchema",
    "BalanceResponseSchema",
    "TransactionResponseSchema",
    "LoanResponseSchema",
    "MessageSchema",
    "AdminActionResponseSchema",
    # Error schemas
    "ErrorResponseSchema",
    "ErrorDetailSchema",
    "ValidationErrorSchema",
    "AuthenticationErrorSchema",
    "AuthorizationErrorSchema",
    "NotFoundErrorSchema",
    "BusinessRuleErrorSchema",
    # Filter schemas
    "AccountFilterSchema",
    "TransactionFilterSchema",
    "LoanFilterSchema",
    "CustomerFilterSchema",
    "ReasonSchema",
    # List schemas
    "PaginationSchema",
    "AccountListItemSchema",
    "AccountListSchema",
    "TransactionListSchema",
    "LoanListSchema",
    "CustomerListSchema",
    # Admin schemas
    "AccountBreakdownSchema",
    "BankFinancialStatusSchema",
    # Utilities
    "SCHEMAS",
    "get_schema",
]
