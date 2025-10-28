"""
Admin and Bank Operator Schemas

Schemas specific to bank operator/admin endpoints.
Includes financial status reporting and account breakdown statistics.
"""

from marshmallow import Schema, fields


# ============================================================================
# ACCOUNT BREAKDOWN
# ============================================================================

class AccountBreakdownSchema(Schema):
    """Schema for account breakdown statistics (simplified for MVP)."""

    total_checking_accounts = fields.Integer(
        required=True, metadata={"description": "Number of active checking accounts"}
    )
    total_loan_accounts = fields.Integer(
        required=True, metadata={"description": "Number of active loan accounts"}
    )
    active_accounts = fields.Integer(
        required=True, metadata={"description": "Total number of active accounts"}
    )


# ============================================================================
# FINANCIAL STATUS
# ============================================================================

class BankFinancialStatusSchema(Schema):
    """
    Schema for bank financial status response.

    Based on fractional reserve banking model:
    - Bank starts with $250,000 capital
    - Can use 25% of customer deposits for lending
    - Must keep 75% of deposits liquid
    """

    bank_capital = fields.Decimal(
        required=True,
        as_string=True,
        places=2,
        metadata={
            "description": "Bank's own capital (not customer money). Currently $250,000 static."
        },
    )
    total_customer_deposits = fields.Decimal(
        required=True,
        as_string=True,
        places=2,
        metadata={
            "description": "Total balance of all active checking accounts (money bank owes customers)"
        },
    )
    usable_customer_deposits = fields.Decimal(
        required=True,
        as_string=True,
        places=2,
        metadata={
            "description": "Portion of deposits available for lending (25% of total deposits)"
        },
    )
    reserved_deposits = fields.Decimal(
        required=True,
        as_string=True,
        places=2,
        metadata={
            "description": "Portion of deposits that must stay liquid for withdrawals (75% of total)"
        },
    )
    total_loans_outstanding = fields.Decimal(
        required=True,
        as_string=True,
        places=2,
        metadata={
            "description": "Total outstanding loan amounts (money customers owe bank, as positive value)"
        },
    )
    available_for_lending = fields.Decimal(
        required=True,
        as_string=True,
        places=2,
        metadata={
            "description": "Total funds available for new loans (capital + 25% deposits - loans). Can be negative if overextended."
        },
    )
    is_overextended = fields.Boolean(
        required=True,
        metadata={
            "description": "True if available_for_lending is negative (bank has lent more than reserves allow)"
        },
    )
    account_breakdown = fields.Nested(
        AccountBreakdownSchema,
        required=True,
        metadata={"description": "Breakdown of accounts by type"},
    )
    as_of = fields.DateTime(
        required=True, metadata={"description": "Timestamp when this status was calculated (UTC)"}
    )
