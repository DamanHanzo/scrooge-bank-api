"""
Integration tests for Admin Bank Endpoints.

Tests the /v1/admin/bank/financial-status endpoint with:
- Authentication requirements
- Authorization (admin-only)
- Response structure and data accuracy

Updated for Bank Capital + Fractional Reserve Model:
- Bank has $250,000 capital
- Can use 25% of customer deposits for lending
"""

from decimal import Decimal

from app.models import Account


class TestAdminBankFinancialStatus:
    """Test suite for bank financial status admin endpoint."""

    def test_get_financial_status_requires_auth(self, client):
        """
        Test that endpoint requires authentication.

        Scenario: Call endpoint without JWT token
        Expected: 401 Unauthorized
        """
        # Act
        response = client.get("/v1/admin/bank/financial-status")

        # Assert
        assert response.status_code == 401

    def test_get_financial_status_requires_admin(self, client, auth_headers):
        """
        Test that endpoint requires admin role.

        Scenario: Call endpoint with regular user token
        Expected: 403 Forbidden with "Admin access required"
        """
        # Act
        response = client.get("/v1/admin/bank/financial-status", headers=auth_headers)

        # Assert
        assert response.status_code == 403
        assert "error" in response.json
        assert "Admin access required" in response.json["error"]["message"]

    def test_get_financial_status_success(
        self, client, admin_auth_headers, db_session, sample_customer
    ):
        """
        Test successful financial status retrieval.

        Scenario: Admin calls endpoint with valid accounts
        Setup: Checking = $75k, Loans = -$125k
        Formula: $250k + (0.25 × $75k) - $125k = $143,750
        Expected: 200 OK with complete financial status
        """
        # Arrange - Create known account balances
        checking = Account(
            customer_id=sample_customer.id,
            account_type="CHECKING",
            account_number="CHK-INTEGRATION",
            status="ACTIVE",
            balance=Decimal("75000.00"),
            currency="USD",
        )
        loan = Account(
            customer_id=sample_customer.id,
            account_type="LOAN",
            account_number="LOAN-INTEGRATION",
            status="ACTIVE",
            balance=Decimal("-125000.00"),
            currency="USD",
        )

        db_session.add_all([checking, loan])
        db_session.commit()

        # Act
        response = client.get("/v1/admin/bank/financial-status", headers=admin_auth_headers)

        # Assert - Status code
        assert response.status_code == 200

        # Assert - Response structure (new fields)
        data = response.json
        assert "bank_capital" in data
        assert "total_customer_deposits" in data
        assert "usable_customer_deposits" in data
        assert "reserved_deposits" in data
        assert "total_loans_outstanding" in data
        assert "available_for_lending" in data
        assert "is_overextended" in data
        assert "account_breakdown" in data
        assert "as_of" in data

        # Assert - Values are correct
        # Deposits: $75k
        # Usable: $18,750 (25%)
        # Reserved: $56,250 (75%)
        # Loans: $125k
        # Available: $250k + $18.75k - $125k = $143.75k
        assert data["bank_capital"] == "250000.00"
        assert data["total_customer_deposits"] == "75000.00"
        assert data["usable_customer_deposits"] == "18750.00"
        assert data["reserved_deposits"] == "56250.00"
        assert data["total_loans_outstanding"] == "125000.00"
        assert data["available_for_lending"] == "143750.00"
        assert data["is_overextended"] is False

        # Assert - Account breakdown
        breakdown = data["account_breakdown"]
        assert breakdown["total_checking_accounts"] == 1
        assert breakdown["total_loan_accounts"] == 1
        assert breakdown["active_accounts"] == 2

    def test_get_financial_status_empty_bank(self, client, admin_auth_headers, db_session):
        """
        Test financial status with no accounts.

        Scenario: Admin calls endpoint when bank has no accounts
        Formula: $250k + (0.25 × $0) - $0 = $250k
        Expected: 200 OK with $250k available (bank capital only)
        """
        # Act
        response = client.get("/v1/admin/bank/financial-status", headers=admin_auth_headers)

        # Assert
        assert response.status_code == 200

        data = response.json
        assert data["bank_capital"] == "250000.00"
        assert data["total_customer_deposits"] == "0.00"
        assert data["usable_customer_deposits"] == "0.00"
        assert data["reserved_deposits"] == "0.00"
        assert data["total_loans_outstanding"] == "0.00"
        assert data["available_for_lending"] == "250000.00"  # Bank capital only
        assert data["is_overextended"] is False
        assert data["account_breakdown"]["total_checking_accounts"] == 0
        assert data["account_breakdown"]["total_loan_accounts"] == 0
        assert data["account_breakdown"]["active_accounts"] == 0

    def test_get_financial_status_bank_overextended(
        self, client, admin_auth_headers, db_session, sample_customer
    ):
        """
        Test financial status when bank is overextended.

        Scenario: Loans exceed capital + usable reserves
        Setup: Deposits = $100k, Loans = $280k
        Formula: $250k + (0.25 × $100k) - $280k = -$5k
        Expected: 200 OK with negative available and is_overextended = True
        """
        # Arrange - Create scenario where bank is overextended
        checking = Account(
            customer_id=sample_customer.id,
            account_type="CHECKING",
            account_number="CHK-OVER-TEST",
            status="ACTIVE",
            balance=Decimal("100000.00"),
            currency="USD",
        )
        loan = Account(
            customer_id=sample_customer.id,
            account_type="LOAN",
            account_number="LOAN-OVER-TEST",
            status="ACTIVE",
            balance=Decimal("-280000.00"),
            currency="USD",
        )

        db_session.add_all([checking, loan])
        db_session.commit()

        # Act
        response = client.get("/v1/admin/bank/financial-status", headers=admin_auth_headers)

        # Assert
        assert response.status_code == 200

        data = response.json
        # Deposits: $100k
        # Usable: $25k (25%)
        # Loans: $280k
        # Available: $250k + $25k - $280k = -$5k (overextended!)
        assert data["bank_capital"] == "250000.00"
        assert data["total_customer_deposits"] == "100000.00"
        assert data["usable_customer_deposits"] == "25000.00"
        assert data["reserved_deposits"] == "75000.00"
        assert data["total_loans_outstanding"] == "280000.00"
        assert data["available_for_lending"] == "-5000.00"
        assert data["is_overextended"] is True
