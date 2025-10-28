"""
Integration tests for Account Lifecycle End-to-End.

These tests validate complete account lifecycle flows:
- Create → List → Close → Verify
- Account creation → closing → new account creation
- Full lifecycle with transactions (deposits/withdrawals)

Tests ensure all components work together correctly.
"""

from decimal import Decimal
from app.models import Account


class TestAccountLifecycle:
    """Test suite for complete account lifecycle scenarios."""

    def test_complete_flow_create_list_close_verify(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Complete flow - Create → List → Close → Verify closed.
        
        Scenario: Happy path through entire account lifecycle
        Steps:
        1. Create account
        2. List accounts (verify it appears)
        3. Close account
        4. List accounts again (verify status is CLOSED)
        """
        with app.app_context():
            # Step 1: Create account
            create_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={
                    'account_type': 'CHECKING',
                    'initial_deposit': 100.00,
                    'currency': 'USD'
                }
            )
            assert create_response.status_code == 201
            account_id = create_response.json['id']
            assert create_response.json['status'] == 'ACTIVE'
            assert create_response.json['balance'] == '100.00'
            
            # Step 2: List accounts (should appear)
            list_response = client.get('/v1/accounts', headers=auth_headers)
            assert list_response.status_code == 200
            assert list_response.json['total'] == 1
            assert list_response.json['data'][0]['id'] == account_id
            assert list_response.json['data'][0]['status'] == 'ACTIVE'
            
            # Step 3: Withdraw all funds to make balance zero
            # (Note: This would require transaction endpoints, so we'll manually update)
            account = db_session.query(Account).filter_by(id=account_id).first()
            account.balance = Decimal('0.00')
            db_session.commit()
            
            # Step 4: Close account
            close_response = client.patch(
                f'/v1/accounts/{account_id}',
                headers=auth_headers,
                json={"status": "CLOSED"}
            )
            assert close_response.status_code == 200
            assert close_response.json['status'] == 'CLOSED'
            
            # Step 5: List accounts again (should show as CLOSED)
            final_list_response = client.get('/v1/accounts', headers=auth_headers)
            assert final_list_response.status_code == 200
            assert final_list_response.json['total'] == 1
            assert final_list_response.json['data'][0]['status'] == 'CLOSED'

    def test_create_account_add_funds_withdraw_all_close(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Create account, add funds, withdraw all, close account.
        
        Scenario: Full account lifecycle with balance changes
        Steps:
        1. Create account with initial deposit
        2. Add more funds (simulated)
        3. Withdraw all funds
        4. Close account (should succeed with zero balance)
        """
        with app.app_context():
            # Step 1: Create account
            create_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={
                    'account_type': 'CHECKING',
                    'initial_deposit': 500.00,
                    'currency': 'USD'
                }
            )
            assert create_response.status_code == 201
            account_id = create_response.json['id']
            assert create_response.json['balance'] == '500.00'
            
            # Step 2: Simulate adding funds
            account = db_session.query(Account).filter_by(id=account_id).first()
            account.balance = Decimal('1500.00')  # Added 1000.00
            db_session.commit()
            
            # Step 3: Simulate withdrawing all funds
            account.balance = Decimal('0.00')
            db_session.commit()
            
            # Step 4: Close account (should succeed)
            close_response = client.patch(
                f'/v1/accounts/{account_id}',
                headers=auth_headers,
                json={"status": "CLOSED"}
            )
            assert close_response.status_code == 200
            assert close_response.json['status'] == 'CLOSED'
            assert close_response.json['balance'] == '0.00'

    def test_create_close_create_new_account_succeeds(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Create account, close it, create new account (should succeed).
        
        Scenario: Customer closes account and opens a new one
        Steps:
        1. Create first account
        2. Close it
        3. Create second account (should succeed - CLOSED accounts don't block)
        Expected: Second account created successfully
        """
        with app.app_context():
            # Step 1: Create first account
            create1_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={
                    'account_type': 'CHECKING',
                    'initial_deposit': 0.00,
                    'currency': 'USD'
                }
            )
            assert create1_response.status_code == 201
            first_account_id = create1_response.json['id']
            first_account_number = create1_response.json['account_number']
            
            # Step 2: Close first account
            close_response = client.patch(
                f'/v1/accounts/{first_account_id}',
                headers=auth_headers,
                json={"status": "CLOSED"}
            )
            assert close_response.status_code == 200
            assert close_response.json['status'] == 'CLOSED'
            
            # Step 3: Create second account (should succeed)
            create2_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={
                    'account_type': 'CHECKING',
                    'initial_deposit': 200.00,
                    'currency': 'USD'
                }
            )
            assert create2_response.status_code == 201
            second_account_id = create2_response.json['id']
            second_account_number = create2_response.json['account_number']
            
            # Verify accounts are different
            assert first_account_id != second_account_id
            assert first_account_number != second_account_number
            
            # Verify second account is active
            assert create2_response.json['status'] == 'ACTIVE'
            assert create2_response.json['balance'] == '200.00'

    def test_customer_can_list_both_active_and_closed_accounts(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Customer with closed account can list both active and closed accounts.
        
        Scenario: Customer has history of closed accounts
        Steps:
        1. Create and close first account
        2. Create second account (keep active)
        3. List all accounts (no filter)
        4. List only ACTIVE accounts
        5. List only CLOSED accounts
        Expected: Can filter and see accounts in different states
        """
        with app.app_context():
            # Step 1: Create and close first account
            create1_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={'account_type': 'CHECKING', 'initial_deposit': 0.00, 'currency': 'USD'}
            )
            first_account_id = create1_response.json['id']
            
            close1_response = client.patch(
                f'/v1/accounts/{first_account_id}',
                headers=auth_headers,
                json={"status": "CLOSED"}
            )
            assert close1_response.status_code == 200
            
            # Step 2: Create second account (keep active)
            create2_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={'account_type': 'CHECKING', 'initial_deposit': 300.00, 'currency': 'USD'}
            )
            assert create2_response.status_code == 201
            
            # Step 3: List all accounts (no filter)
            all_response = client.get('/v1/accounts', headers=auth_headers)
            assert all_response.status_code == 200
            assert all_response.json['total'] == 2
            
            # Step 4: List only ACTIVE accounts
            active_response = client.get('/v1/accounts?status=ACTIVE', headers=auth_headers)
            assert active_response.status_code == 200
            assert active_response.json['total'] == 1
            assert active_response.json['data'][0]['status'] == 'ACTIVE'
            
            # Step 5: List only CLOSED accounts
            closed_response = client.get('/v1/accounts?status=CLOSED', headers=auth_headers)
            assert closed_response.status_code == 200
            assert closed_response.json['total'] == 1
            assert closed_response.json['data'][0]['status'] == 'CLOSED'

    def test_cannot_create_second_active_account(
        self, client, auth_headers, app
    ):
        """
        Test: Cannot create second account while first is still active.
        
        Scenario: Single account rule enforcement
        Steps:
        1. Create first account
        2. Attempt to create second account (should fail)
        Expected: 422 Business Rule Violation
        """
        with app.app_context():
            # Step 1: Create first account
            create1_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={'account_type': 'CHECKING', 'initial_deposit': 100.00, 'currency': 'USD'}
            )
            assert create1_response.status_code == 201
            
            # Step 2: Attempt to create second account
            create2_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={'account_type': 'CHECKING', 'initial_deposit': 50.00, 'currency': 'USD'}
            )
            assert create2_response.status_code == 422
            assert 'already has an open' in create2_response.json['error']['message']

    def test_account_created_without_customer_id_in_request(
        self, client, auth_headers, app
    ):
        """
        Test: Account created without customer_id in request body.
        
        Scenario: Verify customer_id is extracted from JWT, not request
        Steps:
        1. Create account WITHOUT customer_id in body
        2. Verify account is created for authenticated user
        Expected: Account created successfully with customer from JWT
        """
        with app.app_context():
            # Step 1: Create account (no customer_id in body)
            response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={
                    'account_type': 'CHECKING',
                    'initial_deposit': 75.00,
                    'currency': 'USD'
                    # Note: NO customer_id field
                }
            )
            
            # Step 2: Verify success
            assert response.status_code == 201
            assert 'customer_id' in response.json
            assert response.json['status'] == 'ACTIVE'
            assert response.json['balance'] == '75.00'

    def test_full_lifecycle_with_filtering(
        self, client, db_session, sample_customer, auth_headers, app
    ):
        """
        Test: Full lifecycle testing with various filters.
        
        Scenario: Create multiple accounts over time, close some, filter results
        Steps:
        1. Create CHECKING account, close it
        2. Create LOAN account (would be created by loan disbursement)
        3. List with various filters
        Expected: Filtering works correctly throughout lifecycle
        """
        with app.app_context():
            # Step 1: Create and close CHECKING account
            checking_response = client.post(
                '/v1/accounts',
                headers=auth_headers,
                json={'account_type': 'CHECKING', 'initial_deposit': 0.00, 'currency': 'USD'}
            )
            checking_id = checking_response.json['id']
            
            client.patch(f'/v1/accounts/{checking_id}', headers=auth_headers, json={"status": "CLOSED"})
            
            # Step 2: Create LOAN account (manually for testing)
            loan_account = Account(
                customer_id=sample_customer.id,
                account_type="LOAN",
                account_number="LOAN-LIFECYCLE001",
                status="ACTIVE",
                balance=Decimal("-10000.00"),
                currency="USD"
            )
            db_session.add(loan_account)
            db_session.commit()
            
            # Step 3: Test various filters
            # All accounts
            all_resp = client.get('/v1/accounts', headers=auth_headers)
            assert all_resp.json['total'] == 2
            
            # Only LOAN accounts
            loan_resp = client.get('/v1/accounts?account_type=LOAN', headers=auth_headers)
            assert loan_resp.json['total'] == 1
            assert loan_resp.json['data'][0]['account_type'] == 'LOAN'
            
            # Only CHECKING accounts
            checking_resp = client.get('/v1/accounts?account_type=CHECKING', headers=auth_headers)
            assert checking_resp.json['total'] == 1
            assert checking_resp.json['data'][0]['account_type'] == 'CHECKING'
            
            # Only ACTIVE accounts
            active_resp = client.get('/v1/accounts?status=ACTIVE', headers=auth_headers)
            assert active_resp.json['total'] == 1
            assert active_resp.json['data'][0]['status'] == 'ACTIVE'
            
            # ACTIVE LOAN accounts
            active_loan_resp = client.get(
                '/v1/accounts?account_type=LOAN&status=ACTIVE',
                headers=auth_headers
            )
            assert active_loan_resp.json['total'] == 1
            assert active_loan_resp.json['data'][0]['account_type'] == 'LOAN'
            assert active_loan_resp.json['data'][0]['status'] == 'ACTIVE'

