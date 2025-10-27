"""
Integration tests for Account List Endpoint.

Tests the GET /v1/accounts endpoint to validate:
- Authorization (customers see only their accounts, admins can see any)
- Filtering (by account_type, status)
- Response format (data array + total count)
- Error handling (403, 400)

These are integration tests that test the full API endpoint stack.
"""

from decimal import Decimal
from datetime import date

from app.models import Account, Customer


class TestAccountListEndpoint:
    """Test suite for account list endpoint."""

    def test_customer_retrieves_own_accounts(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer retrieves their own accounts.
        
        Scenario: Customer has multiple accounts
        Action: GET /v1/accounts
        Expected: 200 response with list of their accounts
        """
        with app.app_context():
            # Arrange - Create multiple accounts for the customer
            accounts = [
                Account(
                    customer_id=sample_customer.id,
                    account_type="CHECKING",
                    account_number=f"CHK-LIST{i:03d}",
                    status="ACTIVE",
                    balance=Decimal(f"{i * 100}.00"),
                    currency="USD"
                )
                for i in range(1, 4)
            ]
            for acc in accounts:
                db_session.add(acc)
            db_session.commit()
            
            # Act - Get accounts
            response = client.get(
                '/v1/accounts',
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json
            assert 'data' in data
            assert 'total' in data
            assert data['total'] == 3
            assert len(data['data']) == 3
            
            # Verify all returned accounts belong to this customer
            for account in data['data']:
                assert account['customer_id'] == str(sample_customer.id)

    def test_customer_with_no_accounts_gets_empty_list(
        self, client, auth_headers, app
    ):
        """
        Test: Customer with no accounts.
        
        Scenario: Customer has no accounts
        Action: GET /v1/accounts
        Expected: 200 response with empty list and total = 0
        """
        with app.app_context():
            # Act - Get accounts (no accounts created)
            response = client.get(
                '/v1/accounts',
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 0
            assert len(data['data']) == 0

    def test_customer_cannot_list_another_customers_accounts(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer attempts to list another customer's accounts.
        
        Scenario: Customer tries to provide different customer_id in query
        Action: GET /v1/accounts?customer_id={other_id}
        Expected: 403 Forbidden
        """
        with app.app_context():
            # Arrange - Create another customer
            other_customer = Customer(
                email="other@example.com",
                first_name="Other",
                last_name="Customer",
                date_of_birth=date(1991, 1, 1),
                phone="+1-555-8888",
                address_line_1="888 Other St",
                city="Other City",
                state="CA",
                zip_code="88888",
                status="ACTIVE"
            )
            db_session.add(other_customer)
            db_session.commit()
            
            # Act - Try to get other customer's accounts
            response = client.get(
                f'/v1/accounts?customer_id={other_customer.id}',
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 403
            data = response.json
            assert data['error']['code'] == 'FORBIDDEN'

    def test_filter_by_account_type_checking(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer filters by account_type=CHECKING.
        
        Scenario: Customer has both CHECKING and LOAN accounts
        Action: GET /v1/accounts?account_type=CHECKING
        Expected: Only CHECKING accounts returned
        """
        with app.app_context():
            # Arrange - Create CHECKING and LOAN accounts
            checking = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-FILTER001",
                status="ACTIVE",
                balance=Decimal("100.00"),
                currency="USD"
            )
            loan = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-FILTER001",
                status="ACTIVE",
                balance=Decimal("-5000.00"),
                currency="USD"
            )
            db_session.add(checking)
            db_session.add(loan)
            db_session.commit()
            
            # Act - Filter by CHECKING
            response = client.get(
                '/v1/accounts?account_type=CHECKING',
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 1
            assert data['data'][0]['account_type'] == 'CHECKING'

    def test_filter_by_status_active(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer filters by status=ACTIVE.
        
        Scenario: Customer has both ACTIVE and CLOSED accounts
        Action: GET /v1/accounts?status=ACTIVE
        Expected: Only ACTIVE accounts returned
        """
        with app.app_context():
            # Arrange - Create ACTIVE and CLOSED accounts
            active = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-ACTIVE001",
                status="ACTIVE",
                balance=Decimal("100.00"),
                currency="USD"
            )
            closed = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-CLOSED001",
                status="CLOSED",
                balance=Decimal("0.00"),
                currency="USD"
            )
            db_session.add(active)
            db_session.add(closed)
            db_session.commit()
            
            # Act - Filter by ACTIVE status
            response = client.get(
                '/v1/accounts?status=ACTIVE',
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 1
            assert data['data'][0]['status'] == 'ACTIVE'

    def test_filter_by_both_type_and_status(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer filters by both account_type and status.
        
        Scenario: Multiple accounts with different types and statuses
        Action: GET /v1/accounts?account_type=CHECKING&status=ACTIVE
        Expected: Only ACTIVE CHECKING accounts returned
        """
        with app.app_context():
            # Arrange - Create various account combinations
            accounts = [
                Account(customer_id=sample_customer.id, account_type="CHECKING", 
                       account_number="CHK-COMBO1", status="ACTIVE", 
                       balance=Decimal("100.00"), currency="USD"),
                Account(customer_id=sample_customer.id, account_type="CHECKING", 
                       account_number="CHK-COMBO2", status="CLOSED", 
                       balance=Decimal("0.00"), currency="USD"),
                Account(customer_id=sample_customer.id, account_type="LOAN", 
                       account_number="LOAN-COMBO1", status="ACTIVE", 
                       balance=Decimal("-5000.00"), currency="USD"),
            ]
            for acc in accounts:
                db_session.add(acc)
            db_session.commit()
            
            # Act - Filter by CHECKING and ACTIVE
            response = client.get(
                '/v1/accounts?account_type=CHECKING&status=ACTIVE',
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 1
            assert data['data'][0]['account_type'] == 'CHECKING'
            assert data['data'][0]['status'] == 'ACTIVE'

    def test_admin_retrieves_specific_customer_accounts(
        self, client, db_session, sample_customer, admin_auth_headers, app
    ):
        """
        Test: Admin retrieves specific customer's accounts.
        
        Scenario: Admin requests accounts for a specific customer
        Action: GET /v1/accounts?customer_id={customer_id}
        Expected: 200 response with customer's accounts
        """
        with app.app_context():
            # Arrange - Create account for customer
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-ADMIN001",
                status="ACTIVE",
                balance=Decimal("500.00"),
                currency="USD"
            )
            db_session.add(account)
            db_session.commit()
            
            # Act - Admin gets customer's accounts
            response = client.get(
                f'/v1/accounts?customer_id={sample_customer.id}',
                headers=admin_auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 1
            assert data['data'][0]['customer_id'] == str(sample_customer.id)

    def test_admin_without_customer_id_param_gets_error(
        self, client, admin_auth_headers, app
    ):
        """
        Test: Admin without customer_id query parameter.
        
        Scenario: Admin doesn't provide customer_id
        Action: GET /v1/accounts
        Expected: 400 Bad Request
        """
        with app.app_context():
            # Act - Admin request without customer_id
            response = client.get(
                '/v1/accounts',
                headers=admin_auth_headers
            )
            
            # Assert
            assert response.status_code == 400
            data = response.json
            assert data['error']['code'] == 'BAD_REQUEST'
            assert 'customer_id' in data['error']['message']

    def test_response_format_matches_schema(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Verify response format matches schema.
        
        Scenario: Customer has accounts
        Action: GET /v1/accounts
        Expected: Response includes all required fields
        """
        with app.app_context():
            # Arrange
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-SCHEMA001",
                status="ACTIVE",
                balance=Decimal("123.45"),
                currency="USD"
            )
            db_session.add(account)
            db_session.commit()
            
            # Act
            response = client.get(
                '/v1/accounts',
                headers=auth_headers
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json
            
            # Verify top-level structure
            assert 'data' in data
            assert 'total' in data
            assert isinstance(data['data'], list)
            assert isinstance(data['total'], int)
            
            # Verify account object structure
            account_obj = data['data'][0]
            required_fields = ['id', 'customer_id', 'account_type', 
                              'account_number', 'status', 'balance', 
                              'currency', 'created_at']
            for field in required_fields:
                assert field in account_obj, f"Missing field: {field}"
            
            # Verify field values
            assert account_obj['account_number'] == 'CHK-SCHEMA001'
            assert account_obj['balance'] == '123.45'
            assert account_obj['currency'] == 'USD'

    def test_unauthenticated_request_to_list_accounts(
        self, client, app
    ):
        """
        Test: Unauthenticated request to list accounts.
        
        Scenario: No JWT token provided
        Action: GET /v1/accounts without auth headers
        Expected: 401 Unauthorized
        """
        with app.app_context():
            # Act - No auth headers
            response = client.get('/v1/accounts')
            
            # Assert
            assert response.status_code == 401

    def test_customer_only_sees_their_own_accounts_not_others(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer only sees their own accounts, not other customers' accounts.
        
        Scenario: Multiple customers with accounts exist, but customer sees only their own
        Action: GET /v1/accounts
        Expected: Customer sees only their own accounts in the list
        """
        with app.app_context():
            # Arrange - Create another customer with an account
            other_customer = Customer(
                email="other2@example.com",
                first_name="Other",
                last_name="Customer",
                date_of_birth=date(1992, 3, 3),
                phone="+1-555-3333",
                address_line_1="333 Third St",
                city="City",
                state="CA",
                zip_code="33333",
                status="ACTIVE"
            )
            db_session.add(other_customer)
            db_session.commit()
            
            # Create accounts for both customers
            my_account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-MINE001",
                status="ACTIVE",
                balance=Decimal("100.00"),
                currency="USD"
            )
            other_account = Account(
                customer_id=other_customer.id,
                account_type="CHECKING",
                account_number="CHK-OTHER001",
                status="ACTIVE",
                balance=Decimal("200.00"),
                currency="USD"
            )
            db_session.add(my_account)
            db_session.add(other_account)
            db_session.commit()
            
            # Act - Get accounts as sample_customer
            response = client.get('/v1/accounts', headers=auth_headers)
            
            # Assert - Only see my own account
            assert response.status_code == 200
            data = response.json
            assert data['total'] == 1
            assert data['data'][0]['account_number'] == 'CHK-MINE001'
            assert data['data'][0]['customer_id'] == str(sample_customer.id)
            
            # Verify other customer's account is NOT in the list
            account_numbers = [acc['account_number'] for acc in data['data']]
            assert 'CHK-OTHER001' not in account_numbers

