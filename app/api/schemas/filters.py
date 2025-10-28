"""
Filter and Query Parameter Schemas

Schemas for filtering, pagination, and query parameters.
Used with @bp.arguments decorator for query string validation.
"""

from marshmallow import Schema, fields


# ============================================================================
# ACCOUNT FILTERS
# ============================================================================

class AccountFilterSchema(Schema):
    """Schema for filtering accounts (query parameters)."""

    customer_id = fields.UUID(
        required=False,
        metadata={"description": "Filter by customer ID (admin only)"}
    )
    account_type = fields.String(
        required=False,
        validate=lambda x: x in ['CHECKING', 'LOAN'],
        metadata={"description": "Filter by account type", "enum": ["CHECKING", "LOAN"]}
    )
    status = fields.String(
        required=False,
        validate=lambda x: x in ['ACTIVE', 'CLOSED'],
        metadata={"description": "Filter by account status", "enum": ["ACTIVE", "CLOSED"]}
    )


# ============================================================================
# TRANSACTION FILTERS
# ============================================================================

class TransactionFilterSchema(Schema):
    """Query parameters for transaction filtering."""

    start_date = fields.Date(
        required=False, metadata={"description": "Filter transactions from this date"}
    )
    end_date = fields.Date(
        required=False, metadata={"description": "Filter transactions until this date"}
    )
    transaction_type = fields.String(
        required=False,
        metadata={
            "description": "Filter by transaction type",
            "enum": ["DEPOSIT", "WITHDRAWAL", "LOAN_DISBURSEMENT"],
        },
    )
    limit = fields.Integer(load_default=50, metadata={"description": "Number of items per page"})
    offset = fields.Integer(load_default=0, metadata={"description": "Offset from start"})


# ============================================================================
# LOAN FILTERS
# ============================================================================

class LoanFilterSchema(Schema):
    """Query parameters for loan filtering."""

    status = fields.String(
        required=False,
        metadata={
            "description": "Filter by loan status",
            "enum": ["PENDING", "APPROVED", "REJECTED", "CANCELLED", "DISBURSED"],
        },
    )
    limit = fields.Integer(load_default=20)
    offset = fields.Integer(load_default=0)


# ============================================================================
# CUSTOMER FILTERS
# ============================================================================

class CustomerFilterSchema(Schema):
    """Query parameters for customer filtering."""

    status = fields.String(
        required=False,
        metadata={
            "description": "Filter by customer status",
            "enum": ["ACTIVE", "SUSPENDED", "CLOSED"],
        },
    )
    limit = fields.Integer(load_default=50)
    offset = fields.Integer(load_default=0)


# ============================================================================
# GENERIC FILTERS
# ============================================================================

class ReasonSchema(Schema):
    """Optional reason field for admin actions."""

    reason = fields.String(required=False, metadata={"description": "Reason for the action"})
