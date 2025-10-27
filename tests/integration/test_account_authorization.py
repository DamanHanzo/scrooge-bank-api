"""
Integration tests for Account Authorization Scenarios.

These tests validate authorization and access control across all account endpoints:
- Authentication requirements (401 for unauthenticated)
- Customer access control (can only access own accounts)
- Admin access control (can access any accounts with proper params)

Tests ensure proper JWT-based authorization is enforced.
"""


class TestAccountAuthorization:
    """Test suite for account authorization and access control."""

    def test_unauthenticated_create_account_returns_401(self, client, app):
        """
        Test: Unauthenticated request to create account → 401.
        
        Scenario: No JWT token provided
        Action: POST /v1/accounts without auth headers
        Expected: 401 Unauthorized
        """
        with app.app_context():
            response = client.post(
                '/v1/accounts',
                json={'account_type': 'CHECKING', 'initial_deposit': 100.00, 'currency': 'USD'}
            )
            assert response.status_code == 401

    def test_unauthenticated_list_accounts_returns_401(self, client, app):
        """
        Test: Unauthenticated request to list accounts → 401.
        
        Scenario: No JWT token provided
        Action: GET /v1/accounts without auth headers
        Expected: 401 Unauthorized
        """
        with app.app_context():
            response = client.get('/v1/accounts')
            assert response.status_code == 401

    def test_unauthenticated_close_account_returns_401(self, client, app):
        """
        Test: Unauthenticated request to close account → 401.
        
        Scenario: No JWT token provided
        Action: POST /v1/accounts/{id}/close without auth headers
        Expected: 401 Unauthorized
        """
        with app.app_context():
            fake_id = "00000000-0000-0000-0000-000000000000"
            response = client.post(f'/v1/accounts/{fake_id}/close')
            assert response.status_code == 401

    def test_customer_creates_account_without_customer_id_in_body(
        self, client, auth_headers, app
    ):
        """
        Test: Customer creating account (no customer_id in body) → 201.
        
        Scenario: Customer creates account for themselves
        Action: POST /v1/accounts with JWT, no customer_id in body
        Expected: 201 Created, customer_id extracted from JWT
        """
        with app.app_context():
            response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={
                    'account_type': 'CHECKING',
                    'initial_deposit': 150.00,
                    'currency': 'USD'
                    # No customer_id in body
                }
            )
            assert response.status_code == 201
            assert 'customer_id' in response.json
            assert response.json['status'] == 'ACTIVE'

    def test_customer_lists_accounts_sees_only_their_accounts(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer listing accounts → sees only their accounts.
        
        Scenario: Customer requests account list
        Action: GET /v1/accounts
        Expected: 200 OK, only returns accounts belonging to authenticated customer
        """
        with app.app_context():
            from app.models import Account, Customer
            from decimal import Decimal
            from datetime import date
            
            # Create another customer with an account
            other_customer = Customer(
                email="auth_other@example.com",
                first_name="Other",
                last_name="Customer",
                date_of_birth=date(1993, 4, 4),
                phone="+1-555-4444",
                address_line_1="444 Fourth St",
                city="City",
                state="CA",
                zip_code="44444",
                status="ACTIVE"
            )
            db_session.add(other_customer)
            db_session.commit()
            
            # Create accounts for both
            my_account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-AUTH-MINE",
                status="ACTIVE",
                balance=Decimal("100.00"),
                currency="USD"
            )
            other_account = Account(
                customer_id=other_customer.id,
                account_type="CHECKING",
                account_number="CHK-AUTH-OTHER",
                status="ACTIVE",
                balance=Decimal("200.00"),
                currency="USD"
            )
            db_session.add(my_account)
            db_session.add(other_account)
            db_session.commit()
            
            # Customer lists their accounts
            response = client.get('/v1/accounts', headers=auth_headers)
            
            assert response.status_code == 200
            assert response.json['total'] == 1
            assert response.json['data'][0]['account_number'] == 'CHK-AUTH-MINE'

    def test_customer_closes_their_own_account_success(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer closing their own account → 200.
        
        Scenario: Customer closes their own account
        Action: POST /v1/accounts/{own_id}/close
        Expected: 200 OK, account closed
        """
        with app.app_context():
            from app.models import Account
            from decimal import Decimal
            
            # Create account with zero balance
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-AUTH-CLOSE",
                status="ACTIVE",
                balance=Decimal("0.00"),
                currency="USD"
            )
            db_session.add(account)
            db_session.commit()
            
            # Close own account
            response = client.post(
                f'/v1/accounts/{account.id}/close',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.json['status'] == 'CLOSED'

    def test_customer_closing_another_customers_account_returns_403(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer closing another's account → 403.
        
        Scenario: Customer tries to close someone else's account
        Action: POST /v1/accounts/{other_id}/close
        Expected: 403 Forbidden
        """
        with app.app_context():
            from app.models import Account, Customer
            from decimal import Decimal
            from datetime import date
            
            # Create another customer with account
            other_customer = Customer(
                email="auth_other2@example.com",
                first_name="Other",
                last_name="Customer2",
                date_of_birth=date(1994, 5, 5),
                phone="+1-555-5555",
                address_line_1="555 Fifth St",
                city="City",
                state="CA",
                zip_code="55555",
                status="ACTIVE"
            )
            db_session.add(other_customer)
            db_session.commit()
            
            other_account = Account(
                customer_id=other_customer.id,
                account_type="CHECKING",
                account_number="CHK-AUTH-OTHER2",
                status="ACTIVE",
                balance=Decimal("0.00"),
                currency="USD"
            )
            db_session.add(other_account)
            db_session.commit()
            
            # Try to close other's account
            response = client.post(
                f'/v1/accounts/{other_account.id}/close',
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert response.json['error']['code'] == 'FORBIDDEN'

    def test_admin_creates_account_for_customer_with_query_param(
        self, client, db_session, sample_customer, admin_auth_headers, app
    ):
        """
        Test: Admin creating account for customer → requires customer_id param.
        
        Scenario: Admin creates account for a specific customer
        Action: POST /v1/accounts?customer_id={id}
        Expected: 201 Created
        """
        with app.app_context():
            response = client.post(
                f'/v1/accounts?customer_id={sample_customer.id}',
                headers=admin_auth_headers,
                json={
                    'account_type': 'CHECKING',
                    'initial_deposit': 500.00,
                    'currency': 'USD'
                }
            )
            
            assert response.status_code == 201
            assert response.json['customer_id'] == str(sample_customer.id)

    def test_admin_lists_accounts_requires_customer_id_query_param(
        self, client, admin_auth_headers, app
    ):
        """
        Test: Admin listing accounts → requires customer_id query param.
        
        Scenario: Admin tries to list accounts without customer_id
        Action: GET /v1/accounts (no customer_id param)
        Expected: 400 Bad Request
        """
        with app.app_context():
            response = client.get('/v1/accounts', headers=admin_auth_headers)
            
            assert response.status_code == 400
            assert 'customer_id' in response.json['error']['message']

    def test_admin_closes_any_customer_account_success(
        self, client, db_session, sample_customer, admin_auth_headers, app
    ):
        """
        Test: Admin closing any account → 200.
        
        Scenario: Admin closes any customer's account
        Action: POST /v1/accounts/{any_id}/close
        Expected: 200 OK
        """
        with app.app_context():
            from app.models import Account
            from decimal import Decimal
            
            # Create account
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-ADMIN-CLOSE",
                status="ACTIVE",
                balance=Decimal("0.00"),
                currency="USD"
            )
            db_session.add(account)
            db_session.commit()
            
            # Admin closes account
            response = client.post(
                f'/v1/accounts/{account.id}/close',
                headers=admin_auth_headers
            )
            
            assert response.status_code == 200
            assert response.json['status'] == 'CLOSED'

    def test_admin_lists_specific_customer_accounts_with_customer_id(
        self, client, db_session, sample_customer, admin_auth_headers, app
    ):
        """
        Test: Admin can list accounts for specific customer.
        
        Scenario: Admin provides customer_id query parameter
        Action: GET /v1/accounts?customer_id={id}
        Expected: 200 OK with customer's accounts
        """
        with app.app_context():
            from app.models import Account
            from decimal import Decimal
            
            # Create account for customer
            account = Account(
                customer_id=sample_customer.id,
                account_type="CHECKING",
                account_number="CHK-ADMIN-LIST",
                status="ACTIVE",
                balance=Decimal("300.00"),
                currency="USD"
            )
            db_session.add(account)
            db_session.commit()
            
            # Admin lists customer's accounts
            response = client.get(
                f'/v1/accounts?customer_id={sample_customer.id}',
                headers=admin_auth_headers
            )
            
            assert response.status_code == 200
            assert response.json['total'] >= 1
            # Verify at least one account belongs to the customer
            account_found = any(
                acc['customer_id'] == str(sample_customer.id)
                for acc in response.json['data']
            )
            assert account_found

    def test_customer_cannot_access_another_customer_account_via_query_param(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer cannot use customer_id param to view other accounts.
        
        Scenario: Customer tries to provide different customer_id in query
        Action: GET /v1/accounts?customer_id={other_id}
        Expected: 403 Forbidden
        """
        with app.app_context():
            from app.models import Customer
            from datetime import date
            
            # Create another customer
            other_customer = Customer(
                email="auth_other3@example.com",
                first_name="Other",
                last_name="Customer3",
                date_of_birth=date(1995, 6, 6),
                phone="+1-555-6666",
                address_line_1="666 Sixth St",
                city="City",
                state="CA",
                zip_code="66666",
                status="ACTIVE"
            )
            db_session.add(other_customer)
            db_session.commit()
            
            # Try to list other customer's accounts
            response = client.get(
                f'/v1/accounts?customer_id={other_customer.id}',
                headers=auth_headers
            )
            
            assert response.status_code == 403
            assert response.json['error']['code'] == 'FORBIDDEN'

