"""
List and Pagination Schemas

Schemas for paginated list responses and pagination metadata.
"""

from marshmallow import Schema, fields


# ============================================================================
# PAGINATION
# ============================================================================

class PaginationSchema(Schema):
    """Pagination metadata."""

    total = fields.Integer(required=True, metadata={"description": "Total number of items"})
    limit = fields.Integer(required=True, metadata={"description": "Items per page"})
    offset = fields.Integer(required=True, metadata={"description": "Offset from start"})


# ============================================================================
# ACCOUNT LISTS
# ============================================================================

class AccountListItemSchema(Schema):
    """Schema for individual account in list."""

    id = fields.UUID(required=True)
    customer_id = fields.UUID(required=True)
    account_type = fields.String(required=True, metadata={"enum": ["CHECKING", "LOAN"]})
    account_number = fields.String(required=True)
    status = fields.String(required=True, metadata={"enum": ["ACTIVE", "CLOSED"]})
    balance = fields.String(required=True, metadata={"description": "Balance as string"})
    currency = fields.String(required=True)
    created_at = fields.DateTime(required=True)


class AccountListSchema(Schema):
    """List of accounts with total count."""

    data = fields.List(
        fields.Nested(AccountListItemSchema),
        required=True,
        metadata={"description": "List of account objects"}
    )
    total = fields.Integer(required=True, metadata={"description": "Total number of accounts"})


# ============================================================================
# TRANSACTION LISTS
# ============================================================================

class TransactionListSchema(Schema):
    """List of transactions with pagination."""

    data = fields.List(fields.Dict(), required=True)
    pagination = fields.Nested(PaginationSchema, required=True)


# ============================================================================
# LOAN LISTS
# ============================================================================

class LoanListSchema(Schema):
    """List of loan applications with pagination."""

    data = fields.List(fields.Dict(), required=True)
    pagination = fields.Nested(PaginationSchema, required=True)


# ============================================================================
# CUSTOMER LISTS
# ============================================================================

class CustomerListSchema(Schema):
    """List of customers with pagination."""

    data = fields.List(fields.Dict(), required=True)
    pagination = fields.Nested(PaginationSchema, required=True)
